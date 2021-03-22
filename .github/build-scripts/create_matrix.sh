declare -A params_from_tags
params_from_tags[cp36]=3.6
params_from_tags[cp37]=3.7
params_from_tags[cp38]=3.8
params_from_tags[cp39]=3.9
params_from_tags[x86_64]=x64
params_from_tags[i686]=x86

cd wheelhouse
# {distribution}-{version}-{python tag}-{abi tag}-{platform tag}.whl
includes="{\"include\": ["
for wheel in $(ls *.whl)
do
    tags=($(echo $wheel|sed -e 's/-/ /g'))
    python_tag=${tags[2]}
    python_version=${params_from_tags[$python_tag]}
    if [[ ${tags[4]} == manylinux* ]]
    then
        arch_tag=$(echo ${tags[4]} | sed -e 's/.whl//' -e 's/manylinux[0-9]\+_\|manylinux_[0-9]\+_[0-9]\+_//')
        arch=${params_from_tags[$arch_tag]}
        os=ubuntu-latest
    elif [[ ${tags[4]} == macosx* ]]
    then
        arch=x64
        os=macos-latest
    elif [[ ${tags[4]} == win* ]]
    then
        continue
    fi
    includes+=$(printf '{"os":"%s","python-version":"%s","arch":"%s", "package":"%s"},' $os $python_version $arch $wheel)
done
output=$(echo $includes | sed -e 's/,$//')"]}"
echo $output