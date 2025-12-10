; ezText Inno Setup Script
; This script creates an installer that installs to %APPDATA%

#define MyAppName "ezText"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "gloriouslegacy"
#define MyAppURL "https://github.com/gloriouslegacy/ezText"
#define MyAppExeName "ezText.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
AppId={{E7A3F9B2-5C4D-4E8A-9F1B-3D2C8A7E6B5F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
; Install to %APPDATA%\ezText (fixed path, user cannot change)
DefaultDirName={userappdata}\{#MyAppName}
DisableDirPage=yes
; Desktop icon is enabled by default
DefaultGroupName={#MyAppName}
; Output setup file
OutputDir=dist
OutputBaseFilename=ezText-setup
; Icons
SetupIconFile=icon\ezText.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
; Compression
Compression=lzma
SolidCompression=yes
; Windows version
MinVersion=10.0
; Architecture
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Privileges (user level, no admin required)
PrivilegesRequired=lowest

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; Desktop icon task - enabled by default
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
; Main executable
Source: "dist\ezText.exe"; DestDir: "{app}"; Flags: ignoreversion
; Icon file
Source: "icon\ezText.ico"; DestDir: "{app}\icon"; Flags: ignoreversion
; Version file
Source: "version.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu shortcut
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
; Desktop shortcut (controlled by task)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Option to launch the application after installation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up config files on uninstall (optional - you might want to keep user data)
Type: filesandordirs; Name: "{app}"

