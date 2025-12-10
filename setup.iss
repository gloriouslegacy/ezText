; ezText Inno Setup Script
; Creates Windows installer with setup wizard

#define MyAppName "ezText"
; Get version from environment or use default
#define MyAppVersion GetEnv("EZTEXT_VERSION")
#if MyAppVersion == ""
  #define MyAppVersion "1.0.0"
#endif
#define MyAppPublisher "gloriouslegacy"
#define MyAppURL "https://github.com/gloriouslegacy/ezText"
#define MyAppExeName "ezText.exe"

[Setup]
; App information
AppId={{E7A3F9B2-5C4D-4E8A-9F1B-3D2C8A7E6B5F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Installation directories - USER ONLY (Install to %APPDATA%)
DefaultDirName={userappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
DisableDirPage=yes

; Output
OutputDir=installer_output
OutputBaseFilename=ezText_Setup_{#MyAppVersion}

; Compression
Compression=lzma2
SolidCompression=yes

; Windows version requirement
MinVersion=10.0.19041

; Privileges - USER ONLY (no admin required)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline

; UI settings
WizardStyle=modern
SetupIconFile=icon\ezText.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; License (if exists)
;LicenseFile=LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Main executable (onedir build)
Source: "dist\ezText\ezText.exe"; DestDir: "{app}"; Flags: ignoreversion

; Icon folder - optional, only if exists
#ifexist "dist\ezText\icon\ezText.ico"
Source: "dist\ezText\icon\*"; DestDir: "{app}\icon"; Flags: ignoreversion recursesubdirs createallsubdirs
#endif

; Internal dependencies (required for onedir build)
Source: "dist\ezText\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

; Documentation (if exists)
#ifexist "README.md"
Source: "README.md"; DestDir: "{app}"; DestName: "README.txt"; Flags: ignoreversion isreadme
#endif
#ifexist "LICENSE"
Source: "LICENSE"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion
#endif

[Icons]
; Start Menu shortcuts
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop shortcut
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; Quick Launch shortcut
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; Option to run after installation
; Use shellexec to allow UAC elevation prompt if ezText.exe requires admin privileges
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent shellexec

[UninstallDelete]
; Clean up config files on uninstall
Type: files; Name: "{app}\ezTextShortcut.ini"
Type: dirifempty; Name: "{app}"

[Code]
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
  ProcessName: String;
begin
  Result := True;
  ProcessName := 'ezText.exe';

  // Check if ezText.exe is running and close it
  if MsgBox('Please close ezText before continuing installation.' + #13#10 + #13#10 + 'Click OK to automatically close ezText and continue, or Cancel to exit.', mbConfirmation, MB_OKCANCEL) = IDOK then
  begin
    // Try to close the application
    Exec('taskkill.exe', '/IM ' + ProcessName + ' /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Sleep(1500); // Wait for process to terminate
    Result := True;
  end
  else
    Result := False; // User cancelled
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Post-installation tasks can be added here
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
  ProcessName: String;
begin
  ProcessName := 'ezText.exe';

  if CurUninstallStep = usUninstall then
  begin
    // Close ezText.exe if running before uninstall
    if MsgBox('Please close ezText before continuing uninstallation.' + #13#10 + #13#10 + 'Click OK to automatically close ezText and continue.', mbConfirmation, MB_OK) = IDOK then
    begin
      Exec('taskkill.exe', '/IM ' + ProcessName + ' /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      Sleep(1500); // Wait for process to terminate
    end;
  end;
end;

