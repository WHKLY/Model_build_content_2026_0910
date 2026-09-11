运行环境：Python 3.10及以上

安装依赖：
python -m pip install -r requirements.txt

求解问题1：
python solve_q1.py --input "./附件1.xlsx" --template "./附件5/result1.xlsx" --output-dir "./q1_output" --check-nonunique

验证全局最优性：
python verify_q1.py --certificate "./q1_output/certificate_q1.json" --input "./附件1.xlsx"

生成论文图片：
python plot_results.py --file "./q1_output/result1.xlsx" --output-dir "./figures"