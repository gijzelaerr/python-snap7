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
lib_dir=$(get_absolute_path $2)
output_dir=$(get_absolute_path $3)

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    libname=libsnap7.so
else
    libname=libsnap7.dylib
fi

cd $work_dir

wheel=$(ls *.whl | head -n1)
unpack_dir=$wheel-dir
packagename=$(python3 -m wheel unpack $wheel -d $unpack_dir | sed -e 's/.*\/\(.*\)...OK/\1/')
mkdir -p $unpack_dir/$packagename/snap7/lib
mkdir -p $output_dir
mv $lib_dir/$libname  $unpack_dir/$packagename/snap7/lib/$libname
python3 -m wheel pack $unpack_dir/$packagename -d $output_dir
rm -rf $unpack_dir
