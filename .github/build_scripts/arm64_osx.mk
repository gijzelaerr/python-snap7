TargetCPU  :=arm64
OS         :=osx
CXXFLAGS   := -O3 -fPIC -pedantic -target arm64-apple-darwin

# Standard part

include common.mk

# Override the variable to add a target flag
SharedObjectLinkerName :=g++ -shared -fPIC --target=arm64-apple-darwin
