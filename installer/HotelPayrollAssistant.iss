#define MyAppName "Hotel Payroll Assistant"
#define MyAppVersion "0.5.0"
#define MyAppExeName "Hotel Payroll Assistant.exe"

[Setup]
AppId={{BB9E29D4-3EE5-441D-A3E4-4F912540378E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Hotel Payroll Assistant (internal use)
DefaultDirName={localappdata}\Programs\Hotel Payroll Assistant
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=HotelPayrollAssistant_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "..\dist\Hotel Payroll Assistant\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Hotel Payroll Assistant"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Hotel Payroll Assistant"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: checkedonce

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Open Hotel Payroll Assistant"; Flags: nowait postinstall skipifsilent
