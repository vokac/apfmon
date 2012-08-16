#
# Get memcached counts at factory level
#

host=py-stor
port=11211

fids=`curl --connect-timeout 6 -fks -m 10 http://localhost/mon/f/`
[ $? -ne 0 ] && ( echo curl FAIL rrd-factory f; exit 1 )

# loops over factories
for f in $fids; do
  # test for integer
  [ $f -eq $f ] || ( echo Bad fid:; break ) 

  # set q=0 just to count at factory level, not queue level
  q=0
  db=/var/tmp/rrd/job-state-$f-$q.rrd

  r="N"
  for s in fcr frn fex fft fdn; do
    c=""
    c=`memcat --servers $host "py-prod:1:$s$f" | tr -d [:space:]`
    if [ $? -ne 0 ]; then
      echo memcat bad exit $?
    fi
    if [ -z "$c" ]; then 
      c=0
    fi  
    r=$r:$c
  done
  
#  w="W"
#  for s in CREATED RUNNING EXITING FAULT DONE; do
#    c=`curl --connect-timeout 6 -fks -m 10 http://localhost/mon/n/$f/$s/$q`
#    [ $? -ne 0 ] && c=0
#    w=$w:$c
#  done

  rrdtool update $db $r
  if [ $? -ne 0 ]; then
    echo $db $r
  fi
#  echo "rrdtool update $db $r"

done
