Unicode true
!include "MUI2.nsh"
Name "Notetaker Native"
OutFile "..\..\.local\native-qualified\Notetaker-Native-0.3.1-Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\NotetakerNative"
RequestExecutionLevel user
SetCompressor zlib
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
Section "Notetaker"
  SetOutPath "$INSTDIR"
  File /r "..\..\.local\native-qualified\Notetaker\*.*"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateShortcut "$SMPROGRAMS\Notetaker Native.lnk" "$INSTDIR\Notetaker.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NotetakerNative" "DisplayName" "Notetaker Native"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NotetakerNative" "DisplayVersion" "0.3.1"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NotetakerNative" "UninstallString" '"$INSTDIR\Uninstall.exe"'
SectionEnd
Section "Uninstall"
  ; Only installed binaries are removed. The separate per-user library remains.
  Delete "$SMPROGRAMS\Notetaker Native.lnk"
  Delete "$INSTDIR\Notetaker.exe"
  Delete "$INSTDIR\NotetakerService.exe"
  Delete "$INSTDIR\Uninstall.exe"
  Delete "$INSTDIR\READ-ME.md"
  Delete "$INSTDIR\dependency-lock.txt"
  RMDir /r "$INSTDIR\_internal"
  RMDir "$INSTDIR"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NotetakerNative"
SectionEnd
