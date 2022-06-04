#!/bin/csh
#
#set echo
#
# --- Usage:  ./Make_all.com >& Make_all.log
#
# --- make all transport sampling executables
#
# --- set ARCH to the correct value for this machine.
#
source Make_all.src
#
printenv ARCH
#
#if (! -e ../../config/${ARCH}_setup) then
if (! -e ./${ARCH}_setup) then
  echo "ARCH = " $ARCH "  is not supported"
  exit 1
endif
#
# --- programs
# output is an executable file 'tracers'
foreach m ( tracers )
  # 'make' invokes 'Makefile'
  make ${m} ARCH=${ARCH} >&! Make_${m}
  if ($status) then
    echo "Make failed:" ${m}
  else
    echo "Make worked:" ${m}
  endif
  if (-e /usr/bin/ldedit) then
#   try to set medium pages on POWER5+
    /usr/bin/ldedit -bdatapsize=64K -bstackpsize=64K ${m}
  endif
end
