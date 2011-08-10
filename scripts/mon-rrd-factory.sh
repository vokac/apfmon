#
# fast count just for factory level
# summing all queues 

fids=`curl --connect-timeout 6 -fks -m 10 http://localhost/mon/f/`
[ $? -ne 0 ] && ( echo curl FAIL rrd-factory f; exit 1 )

# loops over factories
for f in 0 $fids; do
  # test for integer
  [ $f -eq $f ] || ( echo Bad fid:; break ) 

  # set q=0 just to count at factory level, not queue level
  q=0
  db=/var/tmp/rrd/job-state-$f-$q.rrd

  r="N"
  for s in CREATED RUNNING EXITING FAULT DONE; do
    c=`curl --connect-timeout 6 -fks -m 10 http://localhost/mon/n/$f/$s/$q`
    [ $? -ne 0 ] && ( echo curl FAIL rrd-factory $f $s $q; echo $c; continue )
    r=$r:$c
    # debug FAULT counts causing rrd spikes
    #if [ $f -eq 0 ] && [ $s == 'FAULT' ] && [ $q -eq 0 ]; then date && echo FAULT:$c; fi
  done

  rrdtool update $db $r
#  echo "rrdtool update $db $r"

done
