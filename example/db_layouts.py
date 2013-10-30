"""
Define DB blocks used.
"""

"""
Below data comes from the dataview of DB1
and shows the index of the first row of data
the first 4 bytes are used for DB info

start of a DB:

0	Start_of_PT    0
2.0	Number_of_PTS  450

"""

rc_if_db_1_layout = """

4	RC_IF_ID	INT
6	RC_IF_NAME	STRING[16]

24.0	LockAct		    BOOL    # interlocked or not
24.1	GrpErr		    BOOL    # indicate error
24.2	RuyToStart	    BOOL
24.3	RdyToReset	    BOOL
24.4	LocalAct	    BOOL
24.5	AutAct		    BOOL    # automatic operation
24.6	ManAct		    BOOL    # manual opration
24.7	OoSAct		    BOOL    # Out of service

25.0	FbkOpenOut	    BOOL    # feedback open
25.1	FbkCloseOut	    BOOL    # feedback closed
25.2	FbkRunOut	    BOOL    # feedback running (pump)

26	    PV_LiUnit	    INT
28 	    PV_Li		    REAL

32.0	PV_Out		    BOOL
32.1	FlutAct		    BOOL
32.2	Bad		        BOOL

34      ScaleOut.High	REAL
38      ScaleOut.Low	REAL

# control fields

42.0    OpenAut		    BOOL     # open / close
42.1	CloseAut	    BOOL     # open / close
42.2	StartAut	    BOOL
42.3 	StopAut		    BOOL
42.4	ModLiOp		    BOOL     # enable manual
42.5	AutModLi	    BOOL     # enable automatic control
42.6	ManModLi	    BOOL     # enable manual
42.7 	RstLi		    BOOL
43.0 	BoolValue	    BOOL
43.1    Occupied	    BOOL     # used by route

44 	    SP_Ext	        REAL
48	    RealValue	    REAL
52	    BatchID		    DWORD    # navision order number
56	    StepNo		    DWORD    # step ?
60	    IntValue	    INT
62 	    StringValue	    STRING[32]
96      BatchName	    STRING[32]  # product name / apprears on screen
"""

tank_rc_if_db_layout = """


"""

