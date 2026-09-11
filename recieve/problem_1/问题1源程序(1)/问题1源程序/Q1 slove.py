#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
from datetime import datetime, time
from fractions import Fraction as F
from hashlib import sha256
import json
from math import lcm
from pathlib import Path

import numpy as np
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from scipy.optimize import Bounds, LinearConstraint, linprog, milp
from scipy.sparse import coo_matrix

N = 144
DT = F(1, 6)
ETA_C = F(9, 10)
ETA_D = F(9, 10)
P_MAX = F(5000)
Q = P_MAX * DT
S_MIN, S_MAX, S_INITIAL = F(1200), F(10800), F(6000)
PROGRAM_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = PROGRAM_DIR / "附件1.xlsx"
TOL = 1e-6


def check(condition, message):
    if not condition:
        raise ValueError(message)


def frac(value):
    check(not isinstance(value, bool), '布尔值不能作为电价或功率')
    try:
        number = F(str(value))
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f'非法数字或缺失数据：{value!r}') from exc
    return number


def minute(value):
    if isinstance(value, (datetime, time)):
        return value.hour * 60 + value.minute
    if isinstance(value, (float, int)) and 0 <= value <= 1:
        return round(value * 1440)
    text = str(value).strip().replace(' ', '')
    offset = 1440 if '+1' in text else 0
    fields = text.replace('+1', '').split(':')
    check(len(fields) >= 2, f'无法识别时间：{value}')
    return offset + int(fields[0]) * 60 + int(fields[1])


def hhmm(m):
    return f'{m // 60:02d}:{m % 60:02d}'


INTERVALS = [f'{hhmm(t*10)}-{hhmm((t+1)*10)}' for t in range(N)]


def read_input(path):
    wb = load_workbook(path, read_only=True, data_only=True)
    rows = list(wb.active.values)
    wb.close()
    rows = [r for r in rows[1:] if any(v is not None for v in r)]
    check(len(rows) == N, f'附件1应有144条数据，实际{len(rows)}条')
    times = [minute(r[0]) for r in rows]
    check(times == list(range(10, 1441, 10)), '数据必须按00:10至24:00连续排列')
    p = [frac(r[1]) for r in rows]
    load = [frac(r[2])*DT for r in rows]
    pv = [frac(r[3])*DT for r in rows]
    check(all(v > 0 for v in p), '本模型要求正购电价格；零/负价需另行建模')
    check(all(v >= 0 for v in load+pv), '负载和光伏不能为负')
    return p, load, pv, [str(r[0]) for r in rows]


def build_model(price, load, pv):
    """同时保留有理数稀疏行和浮点矩阵，避免证书使用四舍五入后的数据。"""
    rows, rhs = [], []
    for a in (1 / ETA_C, ETA_D):
        for t in range(N):
            row = {t: F(-1), N+t: a}
            if t:
                row[N+t-1] = -a
            rows.append(row)
            rhs.append(-(load[t]-pv[t]) + (a*S_INITIAL if t == 0 else 0))
    for sign, cap in ((F(1), ETA_C*Q), (F(-1), Q/ETA_D)):
        for t in range(N):
            row = {N+t: sign}
            if t:
                row[N+t-1] = -sign
            rows.append(row)
            rhs.append(cap + (sign*S_INITIAL if t == 0 else 0))
    objective = price + [F(0)]*N
    lower = [F(0)]*N + [S_MIN]*N
    upper = [v+Q for v in load] + [S_MAX]*N
    lower[-1] = upper[-1] = S_INITIAL
    rr, cc, vv = [], [], []
    for i, row in enumerate(rows):
        for j, a in row.items():
            rr.append(i); cc.append(j); vv.append(float(a))
    matrix = coo_matrix((vv, (rr, cc)), shape=(4*N, 2*N)).tocsr()
    return dict(rows=rows, rhs=rhs, f=objective, lower=lower, upper=upper, A=matrix)


def optimize(model, objective=None, cost_lock=None):
    f = np.array(model['f'], dtype=float) if objective is None else objective
    result = linprog(
        f, A_ub=model['A'], b_ub=np.array(model['rhs'], dtype=float),
        A_eq=None if cost_lock is None else np.array(model['f'], dtype=float)[None, :],
        b_eq=None if cost_lock is None else [cost_lock],
        bounds=list(zip(map(float, model['lower']), map(float, model['upper']))),
        method='highs-ds',
        options={'primal_feasibility_tolerance': 1e-9,
                 'dual_feasibility_tolerance': 1e-9},
    )
    if not result.success or result.status != 0:
        raise RuntimeError(f'LP未得到可验证最优解：{result.message}')
    return result


def decode(state, load, pv):
    changes = [state[t+1]-state[t] for t in range(N)]
    charge = [max(v, F(0))/ETA_C for v in changes]
    discharge = [ETA_D*max(-v, F(0)) for v in changes]
    grid = [max(load[t]-pv[t]+charge[t]-discharge[t], F(0)) for t in range(N)]
    surplus = [grid[t]+pv[t]+discharge[t]-load[t]-charge[t] for t in range(N)]
    return dict(state=state, charge=charge, discharge=discharge, grid=grid, surplus=surplus)


def exact_schedule(solution, model, load, pv):
    """恢复有理SOC后逐条精确检查；恢复失败则报错，绝不伪造证书。

    普通LP顶点的SOC由边界及相邻SOC之差的折点决定，候选差值包括
    充放电限额和使g=0的差值。其分母的最小公倍数给出候选格点。
    这是恢复候选的方法；最终证明依靠逐条Fraction验证而非此猜测。
    """
    lattice = 1
    net = [a-b for a, b in zip(load, pv)]
    candidates = [S_MIN, S_MAX, S_INITIAL, ETA_C*Q, Q/ETA_D]
    candidates += [-ETA_C*n for n in net] + [-n/ETA_D for n in net]
    for value in candidates:
        lattice = lcm(lattice, value.denominator)
    state = [S_INITIAL] + [F(round(float(s)*lattice), lattice) for s in solution.x[N:]]
    answer = decode(state, load, pv)
    z = answer['grid'] + state[1:]
    check(all(lo <= v <= hi for v, lo, hi in zip(z, model['lower'], model['upper'])),
          '有理数恢复后的变量越界，未生成最优性证书')
    for i, (row, b) in enumerate(zip(model['rows'], model['rhs'])):
        check(sum(a*z[j] for j, a in row.items()) <= b,
              f'有理数恢复后的约束{i}不满足，未生成最优性证书')
    check(all(c*d == 0 for c, d in zip(answer['charge'], answer['discharge'])),
          '出现同时充放电')
    return answer


def dual_bound(y, model):
    residual = model['f'].copy()
    for yi, row in zip(y, model['rows']):
        for j, a in row.items():
            residual[j] -= a*yi
    bound = sum(b*yi for b, yi in zip(model['rhs'], y))
    bound += sum(min(r*lo, r*hi) for r, lo, hi in
                 zip(residual, model['lower'], model['upper']))
    return bound


def make_certificate(result, model, price, load, pv, answer, input_path):
    upper = sum(p*g for p, g in zip(price, answer['grid']))
    # 不同分母仅影响恢复质量；无论恢复是否准确，只要y<=0就仍是合法下界。
    candidates = []
    for max_den in (10_000, 1_000_000, 100_000_000, 10_000_000_000):
        y = [min(F(0), F(str(v)).limit_denominator(max_den))
             for v in result.ineqlin.marginals]
        candidates.append((dual_bound(y, model), y))
    lower, y = max(candidates, key=lambda item: item[0])
    gap = upper-lower
    check(gap >= 0, '下界大于可行解费用，证书内部错误')
    cert = {
        'format': 'microgrid-q1-rational-certificate-v1',
        'input_sha256': sha256(input_path.read_bytes()).hexdigest(),
        'input_file': input_path.name,
        'interpretation': '10min right endpoints; eta_c=eta_d=0.9; AC power; no sales revenue; supply>=load',
        'price': list(map(str, price)), 'load_energy': list(map(str, load)),
        'pv_energy': list(map(str, pv)),
        'state': list(map(str, answer['state'])), 'grid': list(map(str, answer['grid'])),
        'y': list(map(str, y)), 'upper_bound': str(upper), 'lower_bound': str(lower),
        'gap': str(gap), 'exact_optimal': gap == 0,
    }
    return cert


def milp_crosscheck(price, load, pv, lp_cost):
    """独立建模：g,c,d,s,u，各144变量；u是充/放模式0-1变量。"""
    count = 5*N
    rr, cc, vv, lbs, ubs = [], [], [], [], []
    def add(row, lo, hi):
        k = len(lbs)
        for j, a in row.items():
            rr.append(k); cc.append(j); vv.append(float(a))
        lbs.append(float(lo)); ubs.append(float(hi))
    for t in range(N):
        # g-c+d >= L-V：完整供电不等式。
        add({t: 1, N+t: -1, 2*N+t: 1}, load[t]-pv[t], np.inf)
        row = {N+t: -ETA_C, 2*N+t: 1/ETA_D, 3*N+t: 1}
        if t:
            row[3*N+t-1] = -1
        initial = S_INITIAL if t == 0 else 0
        add(row, initial, initial)
        add({N+t: 1, 4*N+t: -Q}, -np.inf, 0)  # c <= Q*u
        add({2*N+t: 1, 4*N+t: Q}, -np.inf, Q)  # d <= Q*(1-u)
    low = np.zeros(count)
    high = np.r_[np.array(load, float)+float(Q), np.full(2*N, float(Q)),
                 np.full(N, float(S_MAX)), np.ones(N)]
    low[3*N:4*N] = float(S_MIN)
    low[4*N-1] = high[4*N-1] = float(S_INITIAL)
    c = np.r_[np.array(price, float), np.zeros(4*N)]
    integrality = np.r_[np.zeros(4*N, dtype=int), np.ones(N, dtype=int)]
    matrix = coo_matrix((vv, (rr, cc)), shape=(len(lbs), count)).tocsc()
    result = milp(c, integrality=integrality, bounds=Bounds(low, high),
                  constraints=LinearConstraint(matrix, lbs, ubs),
                  options={'mip_rel_gap': 0.0, 'time_limit': 120.0})
    if not result.success or result.status != 0:
        raise RuntimeError(f'MILP对照未证明最优：{result.message}；可用--skip-milp仅保留有理证书')
    check(abs(float(result.fun)-float(lp_cost)) <= 1e-5, 'LP与物理MILP最优费用不一致')
    x = result.x
    activity = matrix @ x
    violation = max(float(np.max(low-x)), float(np.max(x-high)),
                    float(np.max(np.array(lbs)-activity)), float(np.max(activity-np.array(ubs))), 0.)
    check(violation < TOL, 'MILP约束违反超过容差')
    check(np.max(np.abs(x[4*N:]-np.rint(x[4*N:]))) < TOL, 'MILP模式变量不为整数')
    return {'objective': float(result.fun), 'mip_dual_bound': float(result.mip_dual_bound),
            'mip_gap': float(result.mip_gap), 'max_violation': violation}


def nonuniqueness(model, cost, load, pv):
    pivot = INTERVALS.index('23:10-23:20')
    objective = np.zeros(2*N); objective[pivot] = 1
    results = [optimize(model, objective, float(cost)), optimize(model, -objective, float(cost))]
    answers = [exact_schedule(r, model, load, pv) for r in results]
    actual_costs = [sum(p*g for p, g in zip(model['f'][:N], a['grid'])) for a in answers]
    check(all(c == cost for c in actual_costs), '最优面上的候选未通过精确等费用验证')
    different = answers[0]['grid'][pivot] != answers[1]['grid'][pivot]
    return answers, {'pivot': INTERVALS[pivot], 'minimum': str(answers[0]['grid'][pivot]),
                     'maximum': str(answers[1]['grid'][pivot]), 'different': different,
                     'costs_exactly_equal': True,
                     'note': '若different=False，只说明该时段未检出非唯一性，不能据此宣称全方案唯一。'}


def style_sheet(ws):
    ws.freeze_panes = 'B2'
    ws.auto_filter.ref = ws.dimensions
    for cell in ws[1]:
        cell.font = Font(name='微软雅黑', bold=True, color='FFFFFF')
        cell.fill = PatternFill('solid', fgColor='234E70')
        cell.alignment = Alignment(wrap_text=True, vertical='center')
    ws.row_dimensions[1].height = 32
    for column in ws.columns:
        letter = column[0].column_letter
        ws.column_dimensions[letter].width = min(36, max(16, len(str(column[0].value or ''))*1.8))
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            if isinstance(cell.value, (int, float)):
                cell.number_format = '0.000000'


def add_detail(wb, name, answer, price, load, pv, labels):
    ws = wb.create_sheet(name)
    ws.append(['日期','时段','期初储电量','期末储电量','计划购电量',
               '充电量','放电量','电价','负载电量','光伏电量','富余电量',
               '购电费用','附件原始时间标签'])
    for t in range(N):
        g = answer['grid'][t]
        # 附件1仅指某天，日期栏用“代表日”，避免捏造观测日期。
        ws.append(['代表日',INTERVALS[t],float(answer['state'][t]),float(answer['state'][t+1]),
                   float(g),float(answer['charge'][t]),float(answer['discharge'][t]),
                   float(price[t]),float(load[t]),float(pv[t]),float(answer['surplus'][t]),
                   float(price[t]*g),labels[t]])
    style_sheet(ws)


def write_excel(path, template, answer, price, load, pv, labels, cert, alternatives=None):
    if template and template.is_file():
        wb = load_workbook(template)
        check('计划购电量' in wb.sheetnames and '充放电量' in wb.sheetnames, 'result1模板工作表缺失')
    else:
        wb = Workbook(); wb.remove(wb.active)
        wb.create_sheet('计划购电量'); wb.create_sheet('充放电量')
    ws = wb['计划购电量']
    # 模板标签漏00:00—00:10且多次日00:00—00:10；保留结构并显式纠正标签。
    ws.cell(1,1,'时间段'); ws.cell(1,2,'购电量')
    for t, g in enumerate(answer['grid']):
        ws.cell(t+2,1,INTERVALS[t]); ws.cell(t+2,2,float(g))
    style_sheet(ws)
    ws = wb['充放电量']
    for j, header in enumerate(['时间段','充电量','放电量','时刻','储电量'],1):
        ws.cell(1,j,header)
    for k in range(6):
        a,b = 24*k,24*(k+1)
        ws.cell(k+2,1,f'{4*k}:00-{4*(k+1)}:00')
        ws.cell(k+2,2,float(sum(answer['charge'][a:b])))
        ws.cell(k+2,3,float(sum(answer['discharge'][a:b])))
    ws.cell(2,4,'0:00'); ws.cell(2,5,float(answer['state'][0]))
    ws.cell(3,4,'24:00'); ws.cell(3,5,float(answer['state'][-1]))
    style_sheet(ws)
    for name in ['逐时明细','指定时段与汇总','最优性验证','模型说明','最优面最小方案','最优面最大方案']:
        if name in wb.sheetnames:
            del wb[name]
    add_detail(wb,'逐时明细',answer,price,load,pv,labels)
    ws=wb.create_sheet('指定时段与汇总'); ws.append(['项目','数值','单位'])
    for h in (10,12,14,16,18,20):
        ws.append([INTERVALS[h*6],float(answer['grid'][h*6]),'kWh'])
    ws.append(['全天购电量',float(sum(answer['grid'])),'kWh'])
    ws.append(['全天购电费',float(F(cert['upper_bound'])),'元'])
    style_sheet(ws)
    ws=wb.create_sheet('最优性验证'); ws.append(['验证项','数值或结论'])
    ws.append(['精确有理原始费用',cert['upper_bound']]); ws.append(['精确有理对偶下界',cert['lower_bound']])
    ws.append(['精确有理上下界差',cert['gap']]); ws.append(['精确全局最优证书',str(cert['exact_optimal'])])
    ws.append(['证书文件','certificate_q1.json，使用verify_q1.py独立验证'])
    if 'milp' in cert:
        for k,v in cert['milp'].items(): ws.append(['MILP '+k,v])
    if 'nonuniqueness' in cert:
        for k,v in cert['nonuniqueness'].items(): ws.append(['非唯一性 '+k,str(v)])
    style_sheet(ws)
    ws=wb.create_sheet('模型说明'); ws.append(['项目','约定'])
    for item in [('单位','电价元/kWh；功率kW；电量与储电量kWh'),
                 ('时间','输入视为10分钟区间右端点，功率按区间均值，全部144段覆盖00:00—24:00'),
                 ('模板修正','将原模板偏后10分钟的计划购电时间标签改为实际区间；源模板不被覆盖'),
                 ('效率','充电0.9、放电0.9，交流侧功率上限5000kW'),
                 ('边界','S0=S144=6000；1200<=SOC<=10800'),
                 ('富余','供电>=负载；不计售电收入；富余电量为供需不等式松弛量'),
                 ('日期','代表日，不将附件1虚构成2025-01-01的实际观测'),
                 ('精度','Excel存浮点全精度，仅显示6位小数；精确证书使用分数字符串'),
                 ('参考文献','见solve_q1.py文件开头的完整文献与对应章节')]: ws.append(item)
    style_sheet(ws); ws.column_dimensions['B'].width=95
    for row in ws.iter_rows(min_row=2):
        row[1].alignment=Alignment(wrap_text=True,vertical='top')
        ws.row_dimensions[row[0].row].height=32
    if alternatives:
        for name,a in zip(['最优面最小方案','最优面最大方案'],alternatives):
            add_detail(wb,name,a,price,load,pv,labels)
    wb.save(path)
    wb.close()
    # 保存后回读：核对时段、条数和储电数据，而不是只看写入成功。
    check_wb=load_workbook(path,read_only=True,data_only=True)
    rows=list(check_wb['逐时明细'].values)
    check(len(rows)==N+1,'导出逐时明细行数不对')
    check([r[1] for r in rows[1:]]==INTERVALS,'导出时段不对')
    check(abs(rows[1][2]-6000)<TOL and abs(rows[-1][3]-6000)<TOL,'导出SOC边界不对')
    check_wb.close()


def main():
    parser=argparse.ArgumentParser(description='问题1：精确凸LP＋有理最优性证书＋物理MILP交叉验证')
    parser.add_argument('--input',type=Path,default=DEFAULT_INPUT,help='附件1.xlsx路径')
    parser.add_argument('--template',type=Path,help='附件5/result1.xlsx；默认在输入文件旁自动查找')
    parser.add_argument('--output-dir',type=Path,default=Path('q1_output'))
    parser.add_argument('--skip-milp',action='store_true',help='跳过辅助MILP对照；有理证书仍必做')
    parser.add_argument('--check-nonunique',action='store_true',help='固定最优费用检验23:10—23:20购电量的可变范围')
    args=parser.parse_args()
    check(args.input.is_file(),f'找不到输入文件：{args.input}')
    args.output_dir.mkdir(parents=True,exist_ok=True)
    template=args.template if args.template else args.input.parent/'附件5'/'result1.xlsx'
    if args.template:
        check(template.is_file(),f'找不到指定模板：{template}')
    out=args.output_dir/'result1.xlsx'
    check(out.resolve()!=args.input.resolve(), '禁止覆盖附件1')
    check(out.resolve()!=template.resolve(), '输出目录不能覆盖原始result1模板，请选择其他目录')
    price,load,pv,labels=read_input(args.input)
    model=build_model(price,load,pv)
    result=optimize(model)
    answer=exact_schedule(result,model,load,pv)
    cert=make_certificate(result,model,price,load,pv,answer,args.input)
    if not args.skip_milp:
        cert['milp']=milp_crosscheck(price,load,pv,F(cert['upper_bound']))
    alternatives=None
    if args.check_nonunique:
        check(cert['exact_optimal'],'非唯一性检查要求已获得严格零差距证书')
        alternatives,cert['nonuniqueness']=nonuniqueness(model,F(cert['upper_bound']),load,pv)
    certificate_path=args.output_dir/'certificate_q1.json'
    certificate_path.write_text(json.dumps(cert,ensure_ascii=False,indent=2),encoding='utf-8')
    write_excel(out,template,answer,price,load,pv,labels,cert,alternatives)
    print('已保存：',out.resolve())
    print('已保存：',certificate_path.resolve())
    print('精确全局最优证书：', '通过（有理数上下界差严格为0）' if cert['exact_optimal'] else
          f'尚未严格相等；已认证费用区间宽度为{cert["gap"]}元')
    print('请再运行：python verify_q1.py --certificate "'+str(certificate_path)+'" --input "'+str(args.input)+'"')


if __name__=='__main__':
    main()
