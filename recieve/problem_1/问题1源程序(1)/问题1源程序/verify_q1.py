#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""问题1的独立最优性证书核验器，不调用任何优化求解器。

用法：
    python verify_q1.py --certificate q1_output/certificate_q1.json --input "附件1.xlsx"

仅证书验证使用Python标准库；指定--input时用openpyxl核对原始输入。
建议始终指定--input，否则只能证明证书内数据对应模型的最优性，不能
证明证书内数据确实来自用户的附件1。所有核心运算使用Fraction。

证明依据：Boyd & Vandenberghe, Convex Optimization (2004)，
§5.1.3与§5.5.1；https://web.stanford.edu/~boyd/cvxbook/bv_cvxbook.pdf
任意y<=0，r=f-A^Ty，B=b^Ty+sum min(r*l,r*u)是全局下界。
这里直接重建问题1的四组不等式，并用物理调度给出上界U。
U=B严格成立，才输出“精确全局最优”；正gap则仅认证误差上界。
"""

from __future__ import annotations

import argparse
from datetime import datetime, time
from fractions import Fraction as F
from hashlib import sha256
import json
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def input_check(path, certificate, price, load, pv):
    from openpyxl import load_workbook
    require(path.is_file(), f'输入文件不存在：{path}')
    require(sha256(path.read_bytes()).hexdigest()==certificate['input_sha256'],
            '源附件的SHA256与证书不一致；可能读取了别的文件或文件已被修改')
    wb=load_workbook(path,read_only=True,data_only=True)
    rows=[r for r in list(wb.active.values)[1:] if any(v is not None for v in r)]
    wb.close()
    require(len(rows)==144, '源附件的数据行数不是144')
    for t,row in enumerate(rows):
        raw=row[0]
        if isinstance(raw,(time,datetime)):
            m=raw.hour*60+raw.minute
        elif isinstance(raw,(float,int)) and 0<=raw<=1:
            m=round(raw*1440)
        else:
            text=str(raw).strip().replace(' ','')
            fields=text.replace('+1','').split(':')
            m=int(fields[0])*60+int(fields[1])+(1440 if '+1' in text else 0)
        require(m==(t+1)*10, f'源附件第{t+1}个时间标签不符合右端点序列')
        require(F(str(row[1]))==price[t], f'第{t+1}段电价被改动')
        require(F(str(row[2]))/6==load[t], f'第{t+1}段负载被改动')
        require(F(str(row[3]))/6==pv[t], f'第{t+1}段光伏被改动')


def verify(certificate, source=None):
    require(certificate.get('format')=='microgrid-q1-rational-certificate-v1', '不支持的证书版本')
    p=[F(v) for v in certificate['price']]
    load=[F(v) for v in certificate['load_energy']]
    pv=[F(v) for v in certificate['pv_energy']]
    s=[F(v) for v in certificate['state']]
    g=[F(v) for v in certificate['grid']]
    y=[F(v) for v in certificate['y']]
    n=144
    require(all(len(a)==n for a in (p,load,pv,g)) and len(s)==n+1 and len(y)==4*n,
            '数据或证书维数不正确')
    require(all(v>0 for v in p) and all(v>=0 for v in load+pv),'输入符号不符合模型')
    require(all(v<=0 for v in y),'对偶乘子必须非正')
    if source is not None:
        input_check(source,certificate,p,load,pv)

    eta=F(9,10); q=F(5000,6)
    require(s[0]==s[-1]==6000, '初末储电量不是6000')
    require(all(F(1200)<=v<=F(10800) for v in s), '储电量越界')
    for t in range(n):
        delta=s[t+1]-s[t]
        charge=max(delta,F(0))/eta
        discharge=eta*max(-delta,F(0))
        require(F(0)<=charge<=q and F(0)<=discharge<=q, f'第{t+1}段充放电功率越界')
        require(charge*discharge==0, f'第{t+1}段同时充放电')
        require(delta==eta*charge-discharge/eta, f'第{t+1}段SOC递推错误')
        require(g[t]>=0, f'第{t+1}段购电量为负')
        require(g[t]+pv[t]+discharge>=load[t]+charge, f'第{t+1}段供电不足')
        require(g[t]<=load[t]+q, f'第{t+1}段购电超出证书盒上界')

    # 不导入solve_q1，独立重建Az<=b。
    z=g+s[1:]
    f=p+[F(0)]*n
    lo=[F(0)]*n+[F(1200)]*n
    hi=[v+q for v in load]+[F(10800)]*n
    lo[-1]=hi[-1]=F(6000)
    residual=f.copy()
    rhs_dot_y=F(0)
    for group in range(4):
        for t in range(n):
            k=group*n+t
            net=load[t]-pv[t]
            if group in (0,1):
                a=1/eta if group==0 else eta
                row={t:F(-1),n+t:a}
                if t>0: row[n+t-1]=-a
                rhs=-net+(a*6000 if t==0 else 0)
            else:
                a=F(1) if group==2 else F(-1)
                row={n+t:a}
                if t>0: row[n+t-1]=-a
                rhs=(eta*q if group==2 else q/eta)+(a*6000 if t==0 else 0)
            require(sum(a*z[j] for j,a in row.items())<=rhs, f'LP第{k+1}条不等式不满足')
            rhs_dot_y+=rhs*y[k]
            for j,a in row.items(): residual[j]-=a*y[k]
    lower=rhs_dot_y+sum(min(r*l,r*u) for r,l,u in zip(residual,lo,hi))
    upper=sum(a*b for a,b in zip(p,g))
    gap=upper-lower
    require(gap>=0, '证明出现下界大于上界的不可能情况')
    require(lower==F(certificate['lower_bound']), '证书中的下界与独立重算不一致')
    require(upper==F(certificate['upper_bound']), '证书中的上界与独立重算不一致')
    require(gap==F(certificate['gap']), '证书中的差距与独立重算不一致')
    require((gap==0)==certificate['exact_optimal'], '证书的最优性结论字段不正确')
    return {'exact_optimal':gap==0,'gap':str(gap),'verified_input':source is not None}


def main():
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--certificate',type=Path,default=Path('q1_output/certificate_q1.json'))
    parser.add_argument('--input',type=Path,help='建议指定：原始附件1.xlsx，以验证证书来源与每个输入值')
    args=parser.parse_args()
    try:
        cert=json.loads(args.certificate.read_text(encoding='utf-8'))
        result=verify(cert,args.input)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        parser.exit(2,f'证书核验失败：{exc}\n')
    if not result['verified_input']:
        print('未提供--input：以下结论仅针对证书中的数据；尚未核对原始附件。')
    if result['exact_optimal']:
        print('通过：物理调度精确可行，原始费用与对偶下界严格相等，已证明本模型的全局最优。')
    else:
        print('调度可行、上下界有效，但未证明精确最优；距最优费用的误差不超过 '+result['gap']+' 元。')


if __name__=='__main__':
    main()
