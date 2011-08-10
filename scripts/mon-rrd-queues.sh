#
# Count states for all queues
# Loop over all panda queues (qid), note qid=0 will return
# a count for all queues

fids=`curl --connect-timeout 3 -fks -m 5 http://localhost/mon/f/`
[ $? -ne 0 ] && ( echo FAIL rrd-queues f; exit 1 )
qids=`curl --connect-timeout 3 -fks -m 5 http://localhost/mon/r/`
[ $? -ne 0 ] && ( echo FAIL rrd-queues r; exit 1 )
# limit to q summary
#qids=0

# loops over factories
for f in 0 $fids; do
  # test for integer
  [ $f -eq $f ] || ( echo Bad fid:; break )

# loop over panda queues
for q in $qids; do
  # test for integer
  [ $q -eq $q ] || ( echo Bad qid:; break )
  db=/var/tmp/rrd/job-state-$f-$q.rrd

  r="N"
  for s in CREATED RUNNING EXITING FAULT DONE; do
    c=`curl --connect-timeout 3 -ks -m 5 http://localhost/mon/n/$f/$s/$q`
    r=$r:$c
    if [ $f -eq 0 ] && [ $s == 'FAULT' ] && [ $q -eq 0 ]; then date && echo $c; fi
  done

  rrdtool update $db $r
#  echo "rrdtool update $db $r"

done
done
