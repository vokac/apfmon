# produce RRD graphs for PYF webpage

# Loop over all panda queues (qid), note qid=0 will return
# a count for all queues

fids=`curl -fks -m 5 http://localhost/mon/f/`
[ $? -ne 0 ] && ( echo FAIL rrd-png f; exit 1 )
qids=`curl -fks -m 5 http://localhost/mon/r/`
[ $? -ne 0 ] && ( echo FAIL rrd-png r; exit 1 )
# limit
qids=

rrddir=/var/tmp/rrd
media=/var/www/html/media
wm=http://apfmon.lancs.ac.uk/

for f in 0 $fids; do
  # test for integer
  [ $f -eq $f ] || ( echo Bad fid:; break )
# STATES counts
for q in 0 $qids; do
  # test for integer
  [ $q -eq $q ] || ( echo Bad qid:; break )
  db=$rrddir/job-state-$f-$q.rrd

#  for t in 6h 1d 1w ; do
  for t in 1d ; do
    #echo rrdtool graph $media/states-$t-$f-$q.png 
    rrdtool graph $media/states-$t-$f-$q.png \
           --title "Last $t"     \
           --watermark $wm        \
           --start end-$t          \
           --lower-limit 0          \
           --vertical-label "number of jobs" \
           DEF:cr=$db:created:AVERAGE \
           DEF:rn=$db:running:AVERAGE  \
           DEF:ex=$db:exiting:AVERAGE   \
           DEF:ft=$db:fault:AVERAGE      \
           DEF:dn=$db:done:AVERAGE        \
           CDEF:st1=cr,1,\*                \
           CDEF:st2=rn,1,\*                 \
           CDEF:st3=ex,1,\*                  \
           CDEF:st4=ft,1,\*                   \
           CDEF:st5=dn,1,\*                    \
           CDEF:ln1=cr,cr,UNKN,IF               \
           CDEF:ln2=rn,cr,rn,+,UNKN,IF           \
           CDEF:ln3=ex,rn,cr,ex,+,+,UNKN,IF       \
           CDEF:ln4=ft               \
           CDEF:ln5=dn                \
           AREA:st1#ECD748:'CREATED'   \
           STACK:st2#48C4EC:'RUNNING'   \
           STACK:st3#EC9D48:'EXITING'    \
           LINE1:ln1#C9B215               \
           LINE1:ln2#1598C3                \
           LINE1:ln3#CC7016                 \
           LINE3:ln4#cc3118:'FAULT (last hr)'\
           LINE3:ln5#23bc14:'DONE (last hr)'  \
                                >/dev/null
  done
done

done # end fids loop

# style
# http://oss.oetiker.ch/rrdtool-trac/wiki/OutlinedAreaGraph
# http://oss.oetiker.ch/rrdtool/gallery/index.en.html
#           AREA:st6#DDDDDD:ALL                        \
#
# LIGHT   DARK
#RED     #EA644A #CC3118
#ORANGE  #EC9D48 #CC7016
#YELLOW  #ECD748 #C9B215
#GREEN   #54EC48 #24BC14
#BLUE    #48C4EC #1598C3
#PINK    #DE48EC #B415C7
#PURPLE  #7648EC #4D18E4 
