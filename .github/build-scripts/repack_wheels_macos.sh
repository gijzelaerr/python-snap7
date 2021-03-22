cd wheelhouse
for wheelname in $(ls *.whl)
do
dirname=$wheelname-dir
packagename=$(python3 -m wheel unpack $wheelname -d $dirname | sed -e 's/.*\/\(.*\)...OK/\1/')
mkdir -p $dirname/$packagename/snap7/lib
mv $dirname/$packagename/snap7/.dylibs/libsnap7.dylib $dirname/$packagename/snap7/lib/libsnap7.dylib
rm $dirname/$packagename/snap7/__dummy__*.so
rm -rf $dirname/$packagename/snap7/.dylibs
python3 -m wheel pack $dirname/$packagename -d ./
rm -rf $dirname
done
