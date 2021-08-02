$dll_dir = $args[0]
$output_dir = $args[1]
New-Item -ItemType Directory $output_dir
Set-Location dist

$wheel = (Get-ChildItem *.whl)[0]
$dirname = -join($wheel, "-dir")
$unpack_string = $(python3 -m wheel unpack $wheel -d $dirname)
$unpack_string -match ".*: (?<pkgname>.*)...Ok"
$packagename = $matches['pkgname']
$libdir = -join($packagename,"\snap7\lib")
New-Item -ItemType Directory -Path $libdir
Copy-Item ..\snap7-full-1.4.2\release\Windows\$dll_dir\snap7.dll $libdir
python3 -m wheel pack $packagename -d ..\$output_dir
Remove-Item $dirname -Force -Recurse
