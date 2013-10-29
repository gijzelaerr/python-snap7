"""
0	Start_of_PT
2.0	Number_of_PTS
"""

db_1_layout = """ 

4	RC_IF_ID	INT	
6	RC_IF_NAME	STRING[16]		

24.0	LockAct		    BOOL	
24.1	GrpErr		    BOOL
24.2	RuyToStart	    BOOL
24.3	RdyToReset	    BOOL
24.4	LocalAct	    BOOL		
24.5	AutAct		    BOOL		
24.6	ManAct		    BOOL		
24.7	OoSAct		    BOOL	

25.0	FbkOpenOut	    BOOL		
25.1	FbkCloseOut	    BOOL		
25.2	FbkRunOut	    BOOL		

26	    PV_LiUnit	    INT
28 	    PV_Li		    REAL

32.0	PV_Out		    BOOL
32.1	FlutAct		    BOOL
32.2	Bad		        BOOL

34.0    ScaleOut.High	REAL
38.0    ScaleOut.Low	REAL

42.0    OpenAut		    BOOL
42.1	CloseAut	    BOOL
42.2	StartAut	    BOOL
42.3 	StopAut		    BOOL
42.4	ModLiOp		    BOOL
42.5	AutModLi	    BOOL
42.6	ManModLi	    BOOL
42.7 	RstLi		    BOOL
43.0 	BoolValue	    BOOL
43.1    Occupied	    BOOL
44 	    SP_Ext	        REAL
48	    RealValue	    REAL
52	    BatchID		    DWORD
56	    StepNo		    DWORD
60	    IntValue	    INT
62 	    StringValue	    STRING[32]
96      BatchName	    STRING[32]
"""

db1_specification = OrderedDict()

for line in db_1_layout.split('\n'):
    row = line.split()
    if row:
        index, var_name, _type = row
        index = index - 4  # correction, because DB bytes 0,1,2,3 are used.

    db1_specification[var_name] = (index, _type)


class DBObject(object):

    def __init__(self, _bytearray, _specification):

        self._bytearray = _bytearray
        self._specification = _specification

    def __get_item__(self, key):
        """
        Get a specific db field
        """
        pass


