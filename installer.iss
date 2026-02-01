#define MyAppName "PrintHex Agent"
#define MyAppVersion "2.5.2"
#define MyAppExeName "agent.exe"

[Setup]
AppName=PrintHex Agent
AppVersion=2.5.3
DefaultDirName={pf}\PrintHexAgent
DefaultGroupName=PrintHex Agent
OutputDir=Output
OutputBaseFilename=PrintHexAgentSetup
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\agent.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\PrintHex Agent"; Filename: "{app}\agent.exe"
