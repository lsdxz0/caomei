import os
import sys

# 将src目录添加到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.append(src_dir)

# 导入并运行主程序
from main import main

if __name__ == '__main__':
    main()
