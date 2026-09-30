#define MyAppName "SERVIX"
#define MyAppVersion "1.0.0"
#define MyAppExeName "SERVIX.exe"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\SERVIX
DefaultGroupName=SERVIX
OutputDir=..\installer-output
OutputBaseFilename=SERVIX-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"

[Files]
Source: "dist\SERVIX\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\SERVIX"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\SERVIX"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch SERVIX"; Flags: nowait postinstall
