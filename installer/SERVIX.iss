#define MyAppName "SERVIX"
#define MyAppVersion "1.0.1"
#define MyAppExeName "SERVIX.exe"

[Setup]
AppId=SERVIX
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName=SERVIX {#MyAppVersion} Preview
AppPublisher=SERVIX
VersionInfoDescription=SERVIX Service Management Setup
VersionInfoProductName=SERVIX Service Management
SetupIconFile=..\assets\servix.ico
UninstallDisplayIcon={app}\SERVIX.exe
UninstallDisplayName=SERVIX Service Management
DefaultDirName={localappdata}\Programs\SERVIX
DefaultGroupName=SERVIX
OutputDir=..\installer-output
OutputBaseFilename=SERVIX-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern dynamic windows11 hidebevels
WizardSizePercent=130
WizardImageFile=..\assets\installer-light.png
WizardImageFileDynamicDark=..\assets\installer-dark.png
WizardSmallImageFile=..\assets\installer-small.png
WizardSmallImageFileDynamicDark=..\assets\installer-small.png
WizardImageStretch=yes
DisableWelcomePage=no
DisableProgramGroupPage=yes
DisableDirPage=auto
PrivilegesRequired=lowest

[LangOptions]
DialogFontName=Segoe UI
DialogFontSize=10
WelcomeFontName=Segoe UI
WelcomeFontSize=22

[Messages]
SetupWindowTitle=SERVIX Setup
WelcomeLabel1=Install SERVIX
WelcomeLabel2=Your service workspace, ready on this PC.%n%nManage service calls, equipment, calibration and AMC in one place.%n%nChoose Continue to set up SERVIX for your Windows account.
ButtonNext=&Continue
ClickNext=Choose Continue to proceed, or Cancel to exit.
ButtonBack=&Back
ButtonInstall=&Install SERVIX
FinishedHeadingLabel=SERVIX is ready
FinishedLabelNoIcons=SERVIX has been installed successfully.%n%nOpen SERVIX to sign in and start working.
FinishedLabel=SERVIX has been installed successfully.%n%nOpen SERVIX from the Start menu or your desktop shortcut.

[Tasks]
Name: "desktopicon"; Description: "Add SERVIX to my desktop"; GroupDescription: "Shortcuts:"; Flags: checkedonce

[Files]
Source: "..\dist\SERVIX\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\SERVIX"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; AppUserModelID: "SERVIX.Desktop"
Name: "{autodesktop}\SERVIX"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; AppUserModelID: "SERVIX.Desktop"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Open SERVIX"; Flags: nowait postinstall skipifsilent

[Code]
procedure InitializeWizard;
begin
  WizardForm.WelcomeLabel1.Font.Style := [fsBold];
  WizardForm.WelcomeLabel1.Height := ScaleY(64);
  WizardForm.WelcomeLabel2.Top := WizardForm.WelcomeLabel1.Top + WizardForm.WelcomeLabel1.Height + ScaleY(18);
  WizardForm.WelcomeLabel2.Height := ScaleY(190);
  WizardForm.PageNameLabel.Font.Size := 15;
  WizardForm.PageNameLabel.Font.Style := [fsBold];
end;
