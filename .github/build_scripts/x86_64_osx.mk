TargetCPU  :=x86_64
OS         :=osx
CXXFLAGS   := -O3 -fPIC -pedantic -target x86_64-apple-darwin

# Standard part

include common.mk

# Override the variable to add a target flag
SharedObjectLinkerName :=g++ -shared -fPIC --target=x86_64-apple-darwin
