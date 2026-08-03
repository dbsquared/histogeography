"""
digitize_server.py — 本地服务：
1. 提供 digitize.html 与参考图
2. 接收用户点击的州界顶点 (像素坐标)
3. 吸附到参考图真实边线 + 沿边线行走加密成密集边界
4. GCP仿射 → 经纬度，写出 viewer/thirteen_states.geojson / .js
"""
import json, os, math
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
import numpy as np
from PIL import Image
import cv2

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = HERE
VIEWER = os.path.join(WORK, 'viewer')
OV_IMG = os.path.join(VIEWER, 'overview_13states.png')
GEOJSON_OUT = os.path.join(VIEWER, 'thirteen_states.geojson')
JS_OUT = os.path.join(VIEWER, 'thirteen_states.js')

# GCP 仿射 (pixel→lonlat)，已在 13 GCP 上校验
FL = [0.02061693, -0.00035784, 90.41403543]
FA = [-0.00099964, -0.01710138, 45.09665433]
def p2ll(x, y):
    return FL[0]*x + FL[1]*y + FL[2], FA[0]*x + FA[1]*y + FA[2]

# 预计算边线图 (参考图梯度)
_ov = np.asarray(Image.open(OV_IMG).convert('RGB')).astype(np.uint8)
_H, _W = _ov.shape[:2]
_gray = cv2.cvtColor(_ov, cv2.COLOR_RGB2GRAY).astype(np.float32)
gx = cv2.Sobel(_gray, cv2.CV_32F, 1, 0, ksize=3)
gy = cv2.Sobel(_gray, cv2.CV_32F, 0, 1, ksize=3)
_grad = np.sqrt(gx**2 + gy**2)
EDGE = (_grad > 40).astype(np.uint8)
print(f'[server] 边线像素: {int(EDGE.sum()):,} / {_H*_W:,}')

def snap_to_edge(pt, maxd=12):
    x, y = int(round(pt[0])), int(round(pt[1]))
    if 0<=x<_W and 0<=y<_H and EDGE[y,x]:
        return [x, y]
    # 在 maxd 邻域内找最近边线像素
    x0,x1=max(0,x-maxd),min(_W,x+maxd)
    y0,y1=max(0,y-maxd),min(_H,y+maxd)
    sub = EDGE[y0:y1, x0:x1]
    if sub.sum()==0:
        return [x, y]
    ys, xs = np.where(sub)
    best=None; bd=1e9
    for dy,dx in zip(ys,xs):
        d=(dx+x0-x)**2+(dy+y0-y)**2
        if d<bd: bd=d; best=[dx+x0, dy+y0]
    return best

def densify_segment(a, b, band=10):
    """a,b: 已吸附的边线像素。返回 a→b 之间沿参考边线的密集像素序列(不含a,含b)。"""
    a=np.array(a,dtype=float); b=np.array(b,dtype=float)
    d = b-a
    L = np.hypot(d[0], d[1])
    if L < 1:
        return [[int(b[0]),int(b[1])]]
    u = d/L  # 单位方向
    n = np.array([-u[1], u[0]])  # 法向
    # 收集 band 内边线像素
    x0=int(min(a[0],b[0])-band); x1=int(max(a[0],b[0])+band)
    y0=int(min(a[1],b[1])-band); y1=int(max(a[1],b[1])+band)
    x0,x1=max(0,x0),min(_W,x1); y0,y1=max(0,y0),min(_H,y1)
    if x1<=x0 or y1<=y0:
        # 回退：线性插值加密
        npt=max(2,int(L))
        return [[int(a[0]+(b[0]-a[0])*t/npt), int(a[1]+(b[1]-a[1])*t/npt)] for t in range(1,npt+1)]
    sub=EDGE[y0:y1, x0:x1]
    ys,xs=np.where(sub)
    pts=[]
    for dy,dx in zip(ys,xs):
        px,py=dx+x0,dy+y0
        # 垂距
        perp=abs((px-a[0])*n[0]+(py-a[1])*n[1])
        if perp<=band:
            proj=(px-a[0])*u[0]+(py-a[1])*u[1]
            if -band<=proj<=L+band:
                pts.append((proj,px,py))
    pts.sort()
    if len(pts) < 2:
        npt=max(2,int(L))
        return [[int(a[0]+(b[0]-a[0])*t/npt), int(a[1]+(b[1]-a[1])*t/npt)] for t in range(1,npt+1)]
    return [[int(px),int(py)] for _,px,py in pts]

def polygon_dense(verts):
    """verts: 用户点击的顶点(像素)。返回密集边界像素列表。"""
    snapped=[snap_to_edge(v) for v in verts]
    dense=[]
    m=len(snapped)
    for i in range(m):
        a=snapped[i]; b=snapped[(i+1)%m]
        seg=densify_segment(a,b)
        dense.extend(seg)
    if not dense: dense=snapped
    return dense

def build_geojson(polygons, states):
    features=[]
    colors={s[0]:s[1] for s in states}
    # 旧城池数据保留
    old_cities=[]
    if os.path.exists(GEOJSON_OUT):
        try:
            raw=open(GEOJSON_OUT,'rb').read()
            try: old=json.loads(raw.decode('utf-8'))
            except: old=json.loads(raw.decode('utf-8','ignore'))
            for ft in old['features']:
                if ft['geometry']['type']=='Point':
                    old_cities.append(ft)
        except Exception as e:
            print('[warn] read old cities failed:', e)
    for name in [s[0] for s in states]:
        if name not in polygons: continue
        v=polygons[name]
        if len(v)<3: continue
        dense=polygon_dense(v)
        ring=[]
        for x,y in dense:
            lon,lat=p2ll(float(x),float(y))
            ring.append([round(lon,6), round(lat,6)])
        if len(ring)<3: continue
        ring.append(ring[0])
        feat={'type':'Feature','properties':{
            'name':name,'color':colors.get(name),'kind':'thirteen_states',
            'era':'东汉永和五年(140)–建安二十五年(220)','verts':len(ring)-1},
            'geometry':{'type':'Polygon','coordinates':[ring]}}
        features.append(feat)
    features.extend(old_cities)
    out={'type':'FeatureCollection',
         'metadata':{'version':'v20-interactive','method':'user-clicked vertices + edge-snap densification',
                     'source':'汉末十三州地图范例/全览-郡级.png','date':'2026-07-10',
                     'states':len([s[0] for s in states if s[0] in polygons])},
         'features':features}
    return out

class H(SimpleHTTPRequestHandler):
    def _send(self, code, obj):
        self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin','*'); self.end_headers()
        self.wfile.write(json.dumps(obj,ensure_ascii=False).encode('utf-8'))
    def do_GET(self):
        p=urlparse(self.path).path
        if p in ('/','/digitize.html'):
            self.path='/digitize.html'
        return SimpleHTTPRequestHandler.do_GET(self)
    def do_POST(self):
        if self.path!='/export':
            self._send(404,{'ok':False,'error':'not found'}); return
        try:
            ln=int(self.headers.get('Content-Length',0)); body=self.rfile.read(ln)
            data=json.loads(body)  # accepts UTF-8 bytes directly
            polygons=data.get('polygons',{}); states=data.get('states',[])
            out=build_geojson(polygons, states)
            nstates=out['metadata']['states']
            # 备份
            if os.path.exists(GEOJSON_OUT):
                import shutil; shutil.copy2(GEOJSON_OUT, GEOJSON_OUT+'.bak')
            json.dump(out, open(GEOJSON_OUT,'w',encoding='utf-8'), ensure_ascii=False, indent=1)
            js="window.THRTEEN_STATES="+json.dumps(out,ensure_ascii=False,separators=(',',':'))+";"
            open(JS_OUT,'w',encoding='utf-8').write(js)
            self._send(200,{'ok':True,'states':nstates,
                'files':['viewer/thirteen_states.geojson','viewer/thirteen_states.js']})
        except Exception as e:
            import traceback; traceback.print_exc()
            self._send(500,{'ok':False,'error':repr(e)})
    def log_message(self, *a): pass

if __name__ == '__main__':
    os.chdir(VIEWER)
    srv=HTTPServer(('127.0.0.1',8788), H)
    print('[server] http://127.0.0.1:8788/digitize.html')
    srv.serve_forever()
