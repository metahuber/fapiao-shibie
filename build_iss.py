"""生成带版本号的临时 installer.iss 文件"""

import sys

src = open('installer.iss', encoding='utf-8').read()
version = sys.argv[1] if len(sys.argv) > 1 else '1.0.0'
src = src.replace('MyAppVersion "1.1.0"', f'MyAppVersion "{version}"')
open('_installer.iss', 'w', encoding='utf-8').write(src)
print(f'版本: {version}')
