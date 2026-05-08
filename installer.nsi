Unicode true

!include "MUI2.nsh"

Name "数电发票识别工具"
OutFile "dist\数电发票识别工具_Setup_v${VERSION}.exe"
InstallDir "$PROGRAMFILES\数电发票识别工具"
RequestExecutionLevel admin

; 界面
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "SimpChinese"

Section "安装"
  SetOutPath "$INSTDIR"
  File /r "dist\数电发票识别工具\*.*"

  ; 桌面快捷方式
  CreateShortCut "$DESKTOP\数电发票识别工具.lnk" "$INSTDIR\数电发票识别工具.exe"

  ; 开始菜单
  CreateDirectory "$SMPROGRAMS\数电发票识别工具"
  CreateShortCut "$SMPROGRAMS\数电发票识别工具\数电发票识别工具.lnk" "$INSTDIR\数电发票识别工具.exe"
  CreateShortCut "$SMPROGRAMS\数电发票识别工具\卸载数电发票识别工具.lnk" "$INSTDIR\uninstall.exe"

  ; 卸载信息
  WriteUninstaller "$INSTDIR\uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\数电发票识别工具" \
    "DisplayName" "数电发票识别工具"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\数电发票识别工具" \
    "UninstallString" "$INSTDIR\uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\数电发票识别工具" \
    "DisplayVersion" "${VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\数电发票识别工具" \
    "Publisher" "陈凡是我"
SectionEnd

Section "卸载"
  RMDir /r "$INSTDIR"
  Delete "$DESKTOP\数电发票识别工具.lnk"
  RMDir /r "$SMPROGRAMS\数电发票识别工具"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\数电发票识别工具"
SectionEnd
