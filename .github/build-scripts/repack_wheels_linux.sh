cd wheelhouse
for wheelname in $(ls *.whl)
do
dirname=$wheelname-dir
packagename=$(python3 -m wheel unpack $wheelname -d $dirname | sed -e 's/.*\/\(.*\)...OK/\1/')
mkdir -p $dirname/$packagename/snap7/lib
mv $dirname/$packagename/python_snap7.libs/libsnap7-*.so $dirname/$packagename/snap7/lib/libsnap7.so
rm -rf $dirname/$packagename/python_snap7.libs
rm $dirname/$packagename/snap7/__dummy__*.so
python3 -m wheel pack $dirname/$packagename -d ./
rm -rf $dirname
done