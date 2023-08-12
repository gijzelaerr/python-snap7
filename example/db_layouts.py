"""
Define DB blocks used.

Below data comes from the dataview of DB1
and shows the index of the first row of data
the first 4 bytes are used for DB info

start of a DB:

0   Start_of_PT    0
2.0 Number_of_PTS  450

"""

rc_if_db_1_layout = """

4   RC_IF_ID    INT
6   RC_IF_NAME  STRING[16]

24.0    LockAct         BOOL    # interlocked or not
24.1    GrpErr          BOOL    # indicate error
24.2    RuyToStart      BOOL
24.3    RdyToReset      BOOL
24.4    LocalAct        BOOL
24.5    AutAct          BOOL    # automatic operation
24.6    ManAct          BOOL    # manual opration
24.7    OoSAct          BOOL    # Out of service

25.0    FbkOpenOut      BOOL    # feedback open
25.1    FbkCloseOut     BOOL    # feedback closed
25.2    FbkRunOut       BOOL    # feedback running (pump)

26      PV_LiUnit       INT
28      PV_Li           REAL

32.0    PV_Out          BOOL
32.1    FlutAct         BOOL
32.2    Bad             BOOL

34      ScaleOut.High   REAL
38      ScaleOut.Low    REAL

# control fields

42.0    OpenAut         BOOL     # open / close
42.1    CloseAut        BOOL     # open / close
42.2    StartAut        BOOL
42.3    StopAut         BOOL
42.4    ModLiOp         BOOL     # enable manual
42.5    AutModLi        BOOL     # enable automatic control
42.6    ManModLi        BOOL     # enable manual
42.7    RstLi           BOOL
43.0    BoolValue       BOOL
43.1    Occupied        BOOL     # used by route

44      SP_Ext          REAL
48      RealValue       REAL
52      BatchID         DWORD    # navision order number
56      StepNo          DWORD    # step ?
60      IntValue        INT
62      StringValue     STRING[32]
96      BatchName       STRING[32]  # product name / apprears on screen
"""

tank_rc_if_db_layout = """

0       RC_IF_ID         INT
2       RC_IF_NAME       STRING[16]
20      BatchName        STRING[32]
54      BatchID          DWORD
58.0    Occupied         BOOL     # Bezet door Koole PA
60      Status           INT      # Status
62      SubStatus        INT      # Substatus
64      Opdrachtstatus   INT      # Opdrachtstatus (zie enum)
66      Tankstatus       INT      # Tankstatus     (zie enum)
68.0    RC_IF_ERR        BOOL     # Module Fout
68.1    QOk              BOOL     # Module OK Module specifieke parameters
68.2    Unlock           BOOL
70      Cmd              INT      # Commando
72      T_Uit            REAL     # Uitschakeltijd
76      Massa            REAL     # Massa product in tank
80      MaxMassa         REAL     # Maximale capaciteit van tank
84      T_Aflever        REAL     # Aflevertemperatuur
88      T_Max            REAL     # Maximale product temperatuur
92      T_HH             REAL     # Hoog Hoog alarm product temperatuur
96      T_LL             REAL     # Laag Laag alarm product temperatuur
100     T_Schakel        REAL     # Schakeltemperatuur productverwarming
104     T_Warmwater      REAL     # Maximale watertemperatuur verwarming
108     SG               REAL     # Soortelijk gewicht bij temperatuur SG_T
112     SG_T             REAL     # Soortelijk gewicht temperatuur
116     SG_DT            REAL     # Soortelijk gewicht delta T
120     SG_R             INT      # Soortelijk gewicht rekenmethodiek
122     Temp             REAL     # Temperatuur
126.0   Temp_MAX         BOOL     # Tmperatuur boven de maximale producttemperatuur
126.1   Temp_H           BOOL     # Temperatuur te hoog
126.2   Temp_L               BOOL           # Temperatuur te laag
126.3   Temp_BA              BOOL           # Temperatuur boven aflevertemperatuur
126.4   Temp_OS              BOOL           # Temperatuur onder schakeltemperatuur
126.5   Niveau_H             BOOL           # Tankniveau hoog
126.6   Niveau_HH            BOOL           # Tankniveau te hoog
126.7   Niveau_HH_LS         BOOL           # Tankniveau te hoog (Level Switch)
127.0   Bodemdruk_H          BOOL           # Bodemdruk hoog
127.1   Topdruk_HH           BOOL           # Topdruk te hoog
127.2   Niveau_L             BOOL           # Tankniveau laag
127.3   Niveau_LL            BOOL           # Tankniveau te laag
127.4   Inslag_Geblokkeerd   BOOL           # Automatische inslag geblokkeerd
127.5   Uitslag_Geblokkeerd  BOOL           # Automatische uitslag geblokkeerd
127.6   Reload               BOOL           # Herlaad productgegevens via de database
127.7   Stikstof             BOOL           # Stikstofdeken gewenst
128.0   Verwarming           BOOL           # Productverwarming gewenst
128.1   StatusStikstof       BOOL           # Stikstofdeken status
128.2   StatusVerwarming     BOOL           # Productverwarming status
130     Productnaam          STRING[52]     # Productnaam
184     Productcode          STRING[20]     # Productcode
206     VP_T_Max             REAL           # Maximale temperatuur
210     VP_T_Min             REAL           # Minimale temperatuur
214     VP_T_Gem             REAL           # Gemiddelde temperatuur
218     VP_Massa             REAL           # Totale massa verpompt
222     VP_Duur              REAL           # Tijdsduur verpomping
226     T1_N                 REAL           # Aantal metingen
230     T1_MassaBegin        REAL           # Massa aan begin van de meting
234     T1_MassaEind         REAL           # Massa aan het eind van de meting
"""
