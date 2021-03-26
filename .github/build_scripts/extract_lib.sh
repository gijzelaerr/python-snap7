get_absolute_path () {
    if [[ $1 == /* ]]
    then
        echo $1
    else
        echo "$PWD/${1#./}"
    fi
}

# set absolute path for directories from args. Default value is current directory
work_dir=$(get_absolute_path $1)
output_dir=$(get_absolute_path $2)

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    lib_src_path=python_snap7.libs/
    lib_ext=so
    ls_pattern=manylinux
else
    lib_src_path=snap7/.dylibs/
    lib_ext=dylib
    ls_pattern=macosx
fi

cd $work_dir

wheel=$(ls *$ls_pattern*.whl | head -n1)
unpack_dir=$wheel-dir
packagename=$(python3 -m wheel unpack $wheel -d $unpack_dir | sed -e 's/.*\/\(.*\)...OK/\1/')
mv $unpack_dir/$packagename/$lib_src_path/libsnap7*.$lib_ext $output_dir/libsnap7.$lib_ext
rm $wheel
rm -rf $unpack_dir
