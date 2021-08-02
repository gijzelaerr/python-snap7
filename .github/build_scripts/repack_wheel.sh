#!/bin/bash
set -e
echo $PWD

get_absolute_path () {
    if [[ $1 == /* ]]
    then
        echo $1
    else
        echo "$PWD/${1#./}"
    fi
}

unpack_wheel () {
    local wheel=$1
    local unpack_dir=$(mktemp -dt "tempdir.XXX")
    local packagename=$(python3 -m wheel unpack $wheel -d $unpack_dir | sed -e 's/.*\/\(.*\)...OK/\1/')
    echo $unpack_dir/$packagename
}

extract_lib () {
    local wheel=$1
    local package_path=$(unpack_wheel $wheel)
    echo $package_path/$lib_src_path/$lib_name*.$lib_ext
}

repack_wheel () {
    local wheel=$1
    local lib_path=$2
    local output_dir=$3
    local package_path=$(unpack_wheel $wheel)
    mkdir -p $package_path/$lib_dest_path
    mv $lib_path $package_path/$lib_dest_path/$lib_name.$lib_ext
    mkdir -p $output_dir
    python3 -m wheel pack $package_path -d $output_dir
}

lib_dest_path=snap7/lib
lib_name=libsnap7

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    lib_src_path=python_snap7.libs/
    lib_ext=so
    ls_pattern=manylinux
else
    lib_src_path=snap7/.dylibs/
    lib_ext=dylib
    ls_pattern=macosx
fi

# set absolute path for directories from args. Default value is current directory
platform_wheel_dir=$(get_absolute_path $1)
pure_wheel_dir=$(get_absolute_path $2)
output_dir=$(get_absolute_path $3)
echo $(ls -la $platform_wheel_dir)

platform_wheel=$(ls $platform_wheel_dir/*.whl | head -n1)
pure_wheel=$(ls $pure_wheel_dir/*.whl | head -n1)

lib_path=$(extract_lib $platform_wheel)
echo $lib_path
repack_wheel $pure_wheel $lib_path $output_dir
