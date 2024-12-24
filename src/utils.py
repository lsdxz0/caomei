import re

def natural_sort_key(s: str) -> list:
    """
    生成用于自然排序的键
    将字符串中的数字部分转换为整数，以便进行自然排序
    例如：'file1.jpg' < 'file2.jpg' < 'file11.jpg'
    
    Args:
        s: 输入字符串
        
    Returns:
        用于排序的键列表，其中数字部分被转换为整数
    """
    # 将字符串分割成数字和非数字部分
    # 例如 'file123.jpg' 会被分割成 ['file', '123', '.jpg']
    parts = re.split('([0-9]+)', s)
    
    # 将数字字符串转换为整数，非数字部分保持不变
    # 这样在排序时会将数字部分作为数字比较，而不是字符串
    return [int(part) if part.isdigit() else part.lower() for part in parts]
