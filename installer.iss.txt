#define MyAppName "PrintHex Agent"
#define MyAppVersion "2.5.2"
#define MyAppExeName "agent.exe"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={pf}\PrintHexAgent
DefaultGroupName=PrintHex Agent

OutputDir=Output
OutputBaseFilename=PrintHexAgentSetup_{#MyAppVersion}

Compression=lzma
SolidCompression=yes

SetupIconFile=printhex.ico

[Files]
Source: "dist\agent.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\PrintHex Agent"; Filename: "{app}\agent.exe"

[Run]
Filename: "{app}\agent.exe"; Flags: nowait postinstall skipifsilent
