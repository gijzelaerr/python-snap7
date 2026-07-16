"""S7CommPlus zlib preset dictionaries for compressed blob decompression.

Extracted from thomas-v2/S7CommPlusDriver (LGPL-3.0):
  src/S7CommPlusDriver/Core/BlobDecompressor.cs

S7-1200/1500 PLCs compress various XML blobs (interface descriptions,
tag tables, line comments, debug info, etc.) using zlib with a preset
dictionary. Python's zlib.decompress() returns Z_NEED_DICT; we provide
the matching dictionary based on the Adler-32 checksum in the zlib header.

The dictionaries are XML template fragments used as zlib backreference
windows. Stored as UTF-8 strings (they are 100% printable text) and
encoded to bytes at import time.
"""

# BodyDesc (90000001) (Adler-32: 0xefaeae49, 3068 bytes)
_DICT_BODYDESC_90000001 = (
    '<NetworkContainer><Network Lang="LAD_CLASSIC" ProgrammingContext="Plain" Mnemonic="German" RefId="1"'
    '><FlgNet Version="10.5.0.0" Lang="LAD_CLASSIC" Routed="true"><Labels>  <ORef DisplayName="End" RefId'
    '="15" UId="3" /> </Labels><Parts><Part UId="3" Gate="Contact"><Negated PinName="operand" /> </Part><'
    'ORef DisplayName=""Tag_1"" RefId="17" UId="5" /> <Part UId="6" Gate="Add" SrcType="DInt" Card="2" />'
    ' <Part UId="14" Gate="Eq" SrcType="Int" /> <Part UId="2" Gate="Round" SrcType="Real" DestType="DInt"'
    ' /> <ORef DisplayName=""Tag_2"" RefId="27" UId="11" /> <ORef DisplayName="L#345" RefId="14" UId="161'
    '" /> <CRef CallType="FunctionCall" RefId="4" UId="5">  <ORef DisplayName="&quot;Reference_block_numb'
    'er_90&quot;" RefId="3" UId="6" />  <ViewInfo Height="0" /></CRef></Parts><Wires><Wire UId="1">  <Pow'
    'errail />   <PCon UId="4" PinName="IN" />   <ViewInfo Start="true" /> </Wire><Wire UId="3">  <OCon U'
    'Id="5" />   <PCon UId="8" PinName="operand" /> </Wire><Wire UId="7">  <PCon UId="9" PinName="OUT1" /'
    '>   <OCon UId="7" /> </Wire><Wire UId="5">  <Powerrail />   <PCon UId="6" PinName="IN" />   <ViewInf'
    'o Start="true" /> </Wire></Wires></FlgNet><DebugInfo Version="10.5.18.4" TimeStamp="1286967528003138'
    '05" TargetSystem="MC7Plus" Lang="LAD_CLASSIC">  <DebugInfo UId="2" SAC="0" GroupNumber="0" GroupBaha'
    'vior="IN" OperandIndex="0" StatementIndex="0" RefId="4" Type="Bool" BitSize="1"><Ident><NativeDirect'
    ' Type="Bool" Name="NativeLocal SlotBit 0" Scope="NativeLocal" Number="0" Range="SlotBit" /></Ident> '
    ' <DebugInfo UId="2" SAC="0" GroupNumber="9" GroupBahavior="IN" OperandIndex="9" StatementIndex="9" R'
    'efId="5" Flags="NegResult" />   <DebugInfo UId="3" SAC="1" GroupNumber="1" GroupBahavior="IN" Operan'
    'dIndex="1" StatementIndex="1" RefId="5" Flags="NegResult" />   <DebugInfo UId="4" SAC="2" GroupNumbe'
    'r="2" GroupBahavior="OUT" StatementIndex="2" RLO="True" />   <DebugInfo UId="5" SAC="3" GroupNumber='
    '"3" GroupBahavior="OUT" OperandIndex="3" StatementIndex="3" RefId="6" />   <DebugInfo UId="6" SAC="4'
    '" GroupNumber="4" GroupBahavior="OUT" StatementIndex="4" RLO="True" Flags="DIInvalidForKop" />   <De'
    'bugInfo UId="7" SAC="5" GroupNumber="5" GroupBahavior="IN" OperandIndex="5" StatementIndex="5" RefId'
    '="7" />   <DebugInfo UId="8" SAC="6" GroupNumber="6" GroupBahavior="OUT" OperandIndex="6" StatementI'
    'ndex="6" RefId="8" />   <DebugInfo UId="9" SAC="7" GroupNumber="7" GroupBahavior="OUT" OperandIndex='
    '"7" StatementIndex="7" RefId="9" />   <DebugInfo UId="0" SAC="8" GroupNumber="8" GroupBahavior="IN" '
    'OperandIndex="8" StatementIndex="8" RefId="0" Flags="NegResult" />   <DebugInfo UId="5" SAC="56" Gro'
    'upNumber="0" GroupBahavior="OUT" StatementIndex="13" RLO="True" CallParaCount="0"><CallInfo>  <Call '
    'SAC="38" StatementIndex="8" />  <CallExecute SAC="54" StatementIndex="11" />  <NextStatementAfterCal'
    'lExecute SAC="55" StatementIndex="12 />  <CallFrameClear SAC="55" StatementIndex="12" /></CallInfo> '
    ' </DebugInfo></DebugInfo></Network><Network Lang="LAD_CLASSIC" ProgrammingContext="Plain" Mnemonic="'
    'German" RefID="56"></Network></NetworkContainer><NetworkContainer />'
)

# CompilerSettings (90000001) (Adler-32: 0x1398a37f, 442 bytes)
_DICT_COMPILERSETTINGS_90000001 = (
    '<Attribut Key=Value="" />falsetrueChecksFlagsCompilerTypeOptimizationFlagsTargetTypeMC7PlusIECShortW'
    'ires_x002C__x0020_NativePointerEnableAllCheck_Classic<Struct Key="</Struct><Language Key="</Language'
    '><Target></Target><CompilerSettingsDocument Version="</CompilerSettingsDocument>FwVersionLanguageLev'
    "elMlfbPlcFamilyCalleeRenumberingPossibleCommonFBD_CLASSICFBD_IECLAD_CLASSICLAD_IECSTLCreateExtendedD"
    "ebugMonitorArrayLimitsSetFlagAutomatically"
)

# DebugInfo (90000001) (Adler-32: 0x1bac39f0, 189 bytes)
_DICT_DEBUGINFO_90000001 = (
    '<BlockDebugInfo Version="10.5.18.4" TimeStamp="128680924506527258"><Target Type="MC7Plus"><Net Id="0'
    '" EndAddress="60" EndAddressXml="-1" EndStatementIndex="31" /> </Target></BlockDebugInfo>'
)

# DebugInfo_IntfDesc (98000001) (Adler-32: 0x66052b13, 2298 bytes)
_DICT_DEBUGINFO_INTFDESC_98000001 = (
    '<Ident><Base<FBT ReferencedTypesIndex=" ClassicSlot=" VolatileSlot=" RetainSlot="<CompileUnitIdent><'
    'MfbUDT IdentRefID=" RetainParameter=" VolatileParameter=" ClassicParameter="<Multiinstance<IdentCont'
    'ainer><Ident<CrossRefInfo><Access> BlockNumber=" BlockType=" TypeName=" StructureModifiedTS=" Interf'
    'aceModifiedTS=" TypeObjectId=" VersionId=" TypeRId=" RId=" MIRetainPaddedBitSize=" MIVolatilePaddedB'
    'itSize=" MIClassicPaddedBitSize=" MIRetainRelativeBitOffset=" MIVolatileRelativeBitOffset=" MIClassi'
    'cRelativeBitOffset=" Scope=" RefId="<XRefItem<Block UId=" Usage=" Instruction=" NetId=" XRefHidden="'
    ' SlotNumber="<ExternalTypes<Datatype ClassicBitsize=" RetainBitsize=" VolatileBitsize="<ExternalType'
    '<IdentStorage><Part> Multiinstance_StartOfRetainPart=" Multiinstance_StartOfVolatilePart=" Multiinst'
    'ance_StartOfClassicPart="<Values WidestMemberBitsize=" PaddedElementBitsize=" IdentRefId=" OperandTy'
    'pe=" OffsetModifiedTimestamp=" OffsetCompileTimestamp="<CallStackUsage UseAnnotatedOffsets="<?xml ve'
    'rsion="1.0" encoding="utf-16"?><BlockInterface<Usage LibReference="xmlns="http://schemas.siemens.com'
    '/Simatic/ES/11/BlockInterface/Source/V11_01.xsd TypeInfoRuntimeId="<Root<OffsetData XmlPartID=" Bloc'
    'kTypeFamily=" BitSlotCount=" Slot8Count=" Slot16Count=" Slot32Count=" Slot64Count=" SlotSingleDouble'
    'Count=" SlotPointerCount="<SubParts> RIdSlots=" IdentUID=" Parameter=" InterfaceGuid=" BlockObjectID'
    '=" VersionGuid="<DatatypeMember<OffsetDataMap HighestAssignedLocalId="<PayloadTokens LStackBitsize="'
    ' Info_ClassicPartSize=" Info_VolatilePartSize=" Info_RetainPartSize="<MemberLayout Accessibility=" I'
    'nfo_Array_PaddedSubtypeSize=" Info_Array_SubtypeSize=" ClassicBitoffset=" NenaBitoffset=" OffsetSpec'
    'ification="<SizeInfo<ParameterPassing<LibraryInfo> TotalMemberCount=" MFlags=" RelativeBitoffset=" R'
    'emanence="<Part<Payload><PayloadToken PenaltyBytesInBits=" HighestAssignedInternalId=" SubPartIndex='
    '" Info_WidestMember=" PaddedBitsize="<Value Kind=" Version="2.0" xmlns="<Member ChangeCount=" Value='
    '" RepresentationSize=" PassedAs=" RID=" LID=" Type="Section"B#16#W#16#Ret_ValFunctionCLASSIC_PLEASEN'
    "ENA_PLEASEVoidTruetrueFalsefalseS7_Visible3251:52:53:54:55:58DTLUSIntundefUndefRealHMI_Visible0x0200"
    '0001WordRetain0x0000FFFFMandatory<Data ID=" Name=" Base=" Relative=" Size=" PaddedSize=" Path="=">'
)

# ExtRefData (90000001) (Adler-32: 0x9b6a3a92, 1792 bytes)
_DICT_EXTREFDATA_90000001 = (
    '<IdentContainer>  <Ident Name="Tag_2" Scope="Global"><CrossRefInfo>  <XRefItem UId="7" Usage="Read" '
    'Instruction="1" NetId="2" />  <XRefItem UId="8" Usage="Read" Instruction="1" NetId="32" />  <XRefIte'
    'm UId="9" Usage="Read" Instruction="1" NetId="33" />  <XRefItem UId="10" Usage="Read" Instruction="1'
    '" NetId="39" />  <XRefItem UId="11" Usage="Read" Instruction="1" NetId="40" /></CrossRefInfo><Simple'
    'Type Type="Bool" /><Access SubClass="SimpleAccess">  <SimpleAccess Type="Bool" Range="Input" Width="'
    'Bit" ByteNumber="1" BitNumber="1" /></Access>  </Ident></IdentContainer><IdentContainer><Ident Name='
    '"L#345" Scope="Global"><CrossRefInfo><XRefItem UId="161" Usage="Read" Instruction="0" NetId="2" /></'
    'CrossRefInfo><SimpleType Type="DInt" /><Access SubClass="Constant"><Constant Name="L#345" Scope="Glo'
    'bal" Type="DInt" Format="Dec_signed" Width="DWord" Value="5901000000000000" /></Access></Ident></Ide'
    'ntContainer><IdentContainer><Ident Name="1" Scope="Global"><CrossRefInfo><XRefItem UId="31" Usage="R'
    'ead" Instruction="0" NetId="33" /><XRefItem UId="32" Usage="Read" Instruction="0" NetId="39" /><XRef'
    'Item UId="32" Usage="Read" Instruction="0" NetId="40" /><XRefItem UId="73" Usage="Read" Instruction='
    '"0" NetId="41" /></CrossRefInfo><SimpleType Type="Real" /><Access SubClass="SimpleAccess"><SimpleAcc'
    'ess Type="Real" Range="Memory" Width="DWord" ByteNumber="567" BitNumber="0" /></Access></Ident></Ide'
    'ntContainer><IdentContainer><Ident Name="Tag_1" Scope="Global"><CrossRefInfo><XRefItem UId="12" Usag'
    'e="Write" Instruction="0" NetId="16" /><XRefItem UId="18" Usage="Read" Instruction="0" NetId="16" />'
    '</CrossRefInfo><SimpleType Type="Int" /><Access SubClass="SimpleAccess"><SimpleAccess Type="Int" Ran'
    'ge="Memory" Width="Word" ByteNumber="167" BitNumber="0" /></Access></Ident></IdentContainer>'
)

# IdentES (90000001) (Adler-32: 0xdf91b6bb, 1325 bytes)
_DICT_IDENTES_90000001 = (
    '<IdentES version="1.0">  <CoreSubtype>FC</CoreSubtype>  <ObjectTypeInfo>CodeBlockData</ObjectTypeInf'
    "o>  <CompileTime>633706353564000671</CompileTime>  <OnlySymbolicAccess>False</OnlySymbolicAccess>  <"
    'HeaderData Version="0.1" />  <IsSystem>true</IsSystem></IdentES><IdentES version="1.0">  <CoreSubtyp'
    "e>DB</CoreSubtype>  <ObjectTypeInfo>DataBlockData</ObjectTypeInfo>  <CompileTime>633706353581345975<"
    '/CompileTime>  <DatablockType type="SharedDB" oftype="Undef" ofnumber="0" />  <OnlySymbolicAccess>Fa'
    'lse</OnlySymbolicAccess>  <HeaderData Version="0.1" />  <IsSystem>true</IsSystem></IdentES><IdentES '
    'version="1.0">  <CoreSubtype>DB</CoreSubtype>  <ObjectTypeInfo>DataBlockData</ObjectTypeInfo>  <Comp'
    'ileTime>633706353587127743</CompileTime>  <DatablockType type="IDBofSDT" oftype="SDT" ofnumber="0" o'
    'fname="IEC_COUNTER" ofTypeTypeGuid="7e93fc34-5398-48b1-a317-38b8cd37b8e8" ofTypeVersionGuid="007ed7c'
    '6-51bd-405c-b7e5-e1fd3f25a6c0" />  <OnlySymbolicAccess>True</OnlySymbolicAccess>  <HeaderData Versio'
    'n="0.1" />  <IsSystem>false</IsSystem></IdentES><IdentES version="1.0">  <CoreSubtype>OB.ProgramCycl'
    "e</CoreSubtype>  <ObjectTypeInfo>CodeBlockData</ObjectTypeInfo>  <CompileTime>633706354424546519</Co"
    'mpileTime>  <OnlySymbolicAccess>False</OnlySymbolicAccess>  <HeaderData Version="0.1" />  <IsSystem>'
    "true</IsSystem></IdentES>"
)

# IdentES (90000002) (Adler-32: 0x81d8db20, 1436 bytes)
_DICT_IDENTES_90000002 = (
    '<IdentES version="1.0">  <CoreSubtype>FC</CoreSubtype>  <ObjectTypeInfo>CodeBlockData</ObjectTypeInf'
    "o>  <CompileTime>633706353564000671</CompileTime>  <OnlySymbolicAccess>False</OnlySymbolicAccess>  <"
    'IecCheck>False</IecCheck>  <HeaderData Version="0.1" />  <IsSystem>true</IsSystem></IdentES><IdentES'
    ' version="1.0">  <CoreSubtype>DB</CoreSubtype>  <ObjectTypeInfo>DataBlockData</ObjectTypeInfo>  <Com'
    'pileTime>633706353581345975</CompileTime>  <DatablockType type="SharedDB" oftype="Undef" ofnumber="0'
    '" />  <OnlySymbolicAccess>False</OnlySymbolicAccess>  <IecCheck>False</IecCheck>  <HeaderData Versio'
    'n="0.1" />  <IsSystem>true</IsSystem></IdentES><IdentES version="1.0">  <CoreSubtype>DB</CoreSubtype'
    ">  <ObjectTypeInfo>DataBlockData</ObjectTypeInfo>  <CompileTime>633706353587127743</CompileTime>  <D"
    'atablockType type="IDBofSDT" oftype="SDT" ofnumber="0" ofname="IEC_COUNTER" ofTypeTypeGuid="7e93fc34'
    '-5398-48b1-a317-38b8cd37b8e8" ofTypeVersionGuid="007ed7c6-51bd-405c-b7e5-e1fd3f25a6c0" />  <OnlySymb'
    'olicAccess>True</OnlySymbolicAccess>  <IecCheck>True</IecCheck>  <HeaderData Version="0.1" />  <IsSy'
    'stem>false</IsSystem></IdentES><IdentES version="1.0">  <CoreSubtype>OB.ProgramCycle</CoreSubtype>  '
    "<ObjectTypeInfo>CodeBlockData</ObjectTypeInfo>  <CompileTime>633706354424546519</CompileTime>  <Only"
    'SymbolicAccess>False</OnlySymbolicAccess>  <IecCheck>False</IecCheck>  <HeaderData Version="0.1" /> '
    " <IsSystem>true</IsSystem></IdentES>"
)

# IdentES (98000001) (Adler-32: 0x5814b03b, 1273 bytes)
_DICT_IDENTES_98000001 = (
    '<IdentES version="1.0"><CoreSubtype>FC</CoreSubtype><ObjectTypeInfo>CodeBlockData</ObjectTypeInfo><C'
    "ompileTime>633706353564000671</CompileTime><OnlySymbolicAccess>False</OnlySymbolicAccess><HeaderData"
    ' Version="0.1" /><IsSystem>true</IsSystem></IdentES><IdentES version="1.0"><CoreSubtype>DB</CoreSubt'
    "ype><ObjectTypeInfo>DataBlockData</ObjectTypeInfo><CompileTime>633706353581345975</CompileTime><Data"
    'blockType type="SharedDB" oftype="Undef" ofnumber="0" /><OnlySymbolicAccess>False</OnlySymbolicAcces'
    's><HeaderData Version="0.1" /><IsSystem>true</IsSystem></IdentES><IdentES version="1.0"><CoreSubtype'
    ">DB</CoreSubtype><ObjectTypeInfo>DataBlockData</ObjectTypeInfo><CompileTime>633706353587127743</Comp"
    'ileTime><DatablockType type="IDBofSDT" oftype="SDT" ofnumber="0" ofname="IEC_COUNTER" ofTypeTypeGuid'
    '="7e93fc34-5398-48b1-a317-38b8cd37b8e8" ofTypeVersionGuid="007ed7c6-51bd-405c-b7e5-e1fd3f25a6c0" /><'
    'OnlySymbolicAccess>True</OnlySymbolicAccess><HeaderData Version="0.1" /><IsSystem>false</IsSystem></'
    'IdentES><IdentES version="1.0"><CoreSubtype>OB.ProgramCycle</CoreSubtype><ObjectTypeInfo>CodeBlockDa'
    "ta</ObjectTypeInfo><CompileTime>633706354424546519</CompileTime><OnlySymbolicAccess>False</OnlySymbo"
    'licAccess><HeaderData Version="0.1" /><IsSystem>true</IsSystem></IdentES>'
)

# IntRefData (90000001) (Adler-32: 0xda4a88f4, 2003 bytes)
_DICT_INTREFDATA_90000001 = (
    '<IdentContainer><Ident Name="End" Scope="Label" RefID="2"><Access SubClass="Label"><Ident /></Access'
    '></Ident><Ident Name="CompileUnit 0" Scope="Number" RefID="3"><Access SubClass="CompileUnitIdent"><C'
    'ompileUnitIdent /></Access></Ident><Ident Name="Reference_block_number_01" Scope="Undef" RefID="4"><'
    'Access SubClass="BlockInterfaceInfo"><BlockInterface RefName="Reference_block_number_01" Number="1" '
    'CalleeType="Block_FC" TypeOperandRefId="80" ParamModificationTS="128660375612413177" /></Access></Id'
    'ent></IdentContainer><Ident Name="Tag_1" Scope="Global" RefID="3"><SimpleType Type="Bool" /><Access '
    'SubClass="SimpleAccess">  <SimpleAccess Type="Bool" Range="Input" Width="Bit" ByteNumber="1" BitNumb'
    'er="0" /></Access></Ident><Ident Name="Tag_5" Scope="Global" RefID="7"><SimpleType Type="Int" /><Acc'
    'ess SubClass="SimpleAccess">  <SimpleAccess Type="Int" Range="Input" Width="Word" ByteNumber="0" Bit'
    'Number="0" /></Access></Ident><Ident Name="Tag_12" Scope="Global" RefID="13"><SimpleType Type="DInt"'
    ' /><Access SubClass="SimpleAccess">  <SimpleAccess Type="DInt" Range="Input" Width="DWord" ByteNumbe'
    'r="1" BitNumber="0" /></Access></Ident><Ident Name="Tag_32" Scope="Global" RefID="34"><SimpleType Ty'
    'pe="Real" /><Access SubClass="SimpleAccess">  <SimpleAccess Type="Real" Range="Memory" Width="DWord"'
    ' ByteNumber="567" BitNumber="0" /></Access></Ident><Ident Name="Reference_block_number_91" Scope="Gl'
    'obal" RefID="6"><SimpleType Type="Block_FC" /><Access SubClass="FCBlock">  <Block Name="Reference_bl'
    'ock_number_91" Scope="Global" Type="Block_FC" Number="91" /></Access></Ident><Ident Name="TP_1a" Sco'
    'pe="Global" RefID="79"><SimpleType Type="Block_DB" /><Access SubClass="Operand">  <Block Name="TP_1a'
    '" Scope="Global" Type="Block_DB" Number="37" /></Access></Ident><Ident Name="T#2s" Scope="Global" Re'
    'fID="80"><SimpleType Type="Time" /><Access SubClass="Constant">  <Constant Name="T#2s" Scope="Global'
    '" Type="Time" Format="Time" Width="DWord" Value="D007000000000000" /></Access></Ident></IdentContain'
    "er>"
)

# IntRefData (98000001) (Adler-32: 0xb0155ff8, 1018 bytes)
_DICT_INTREFDATA_98000001 = (
    '<MultiInstanceAccess ClassicAbsOffset=" RetainAbsOffset=" VolatileAbsOffset="<Label>TypeObjectId=" T'
    'ypeRId="<FBBlock<Instruction<BlockInterfaceInfo OriginalPartName="<IdentContainer><FCBlock LibraryOb'
    'jId=" NeedsInstance="<AufDBBlock CreationId=" VersionId="<DepDBBlock TemplateReference=" ParameterMo'
    'difiedTS="<Parameter ArrayType="<InterfaceAccess InterfaceModifiedTS="<SimpleAccess<Constant<Compile'
    'UnitIdent> StructureModifiedTS=" BlockType=" Section=" Area=" InterfaceFlags="S7_Visible"InterfaceFl'
    'ags="Mandatory, S7_Visible"<GlobalAccess Range=" SimpleAccessModifier=" Format=" Value=" FormatFlags'
    '=" DbNumber="<AccessObject /></Access></Ident><Ident Name=" /><CrossRefInfo><Access><MfbUDT BlockNum'
    'ber=" AbsOffset=" AccessModifier=" TypeName=" RId=" /><XRefItem Scope="Number"Global"Lokal"Constant"'
    ' RefId=" Version="1.0" Type=" UId="1 Usage="Read"None"Multiinstance" Instruction="0" NetId="1 XRefHi'
    'dden="False" Usage="Write"Int"UInt"Real"USInt"Word"DInt"Bool"SInt"Byte"Time"UDInt"DWord"Char"DTL"LRe'
    'al"String"true"=">'
)

# IntfDesc (90000001) (Adler-32: 0x4b8416f0, 4942 bytes)
_DICT_INTFDESC_90000001 = (
    '<?xml version="1.0" encoding="utf-16"?><BlockInterface Version="1.0">  <Source Version="1.0"><Sectio'
    'n Name="Static">  <Line LId="9" Name="START" Symbol="Time" Library.Size="32" Library.Layout.ByteOffs'
    'et="0" Remanence="Volatile" RId="0x200000b" />  <Line LId="10" Name="PRESET" Symbol="Time" Library.S'
    'ize="32" Library.Layout.ByteOffset="4" Remanence="Volatile" RId="0x200000b" />  <Line LId="11" Name='
    '"ELAPSED" Symbol="Time" Library.Size="32" Library.Layout.ByteOffset="8" Remanence="Volatile" RId="0x'
    '200000b" />  <Line LId="12" Name="RUNNING" Symbol="Bool" Library.Size="1" Library.Layout.BitOffset="'
    '12.0" Remanence="Volatile" RId="0x2000001" />  <Line LId="13" Name="IN" Symbol="Bool" Library.Size="'
    '1" Library.Layout.BitOffset="12.1" Remanence="Volatile" RId="0x2000001" />  <Line LId="14" Name="Q" '
    'Symbol="Bool" Library.Size="1" Library.Layout.BitOffset="12.2" Remanence="Volatile" RId="0x2000001" '
    '/>  <Line LId="15" Name="PAD" Symbol="Byte" Library.Size="8" Library.Layout.ByteOffset="13" Remanenc'
    'e="Volatile" RId="0x2000002" />  <Line LId="16" Name="PAD_1" Symbol="Byte" Library.Size="8" Library.'
    'Layout.ByteOffset="14" Remanence="Volatile" RId="0x2000002" />  <Line LId="17" Name="PAD_2" Symbol="'
    'Byte" Library.Size="8" Library.Layout.ByteOffset="15" Remanence="Volatile" RId="0x2000002" /></Secti'
    "on>  </Source>  <StartValues><dictionary_entries></dictionary_entries>  </StartValues></BlockInterfa"
    'ce><?xml version="1.0" encoding="utf-16"?><BlockInterface Version="1.0">  <Source Version="1.0" Next'
    'FreeLId="10" ClassicSize="0" RetainSize="0" VolatileSize="0" Library.LStackBitsize="0"><Section Name'
    '="Input" /><Section Name="Output" /><Section Name="InOut" /><Section Name="Temp" /><Section Name="Re'
    'turn">  <Line Name="Ret_Val" Symbol="Void" LId="9" Accessibility="Public" Remanence="Volatile" Libra'
    'ry.Size="0" Library.Layout.ByteOffset="0" RId="0x2000000" /></Section>  </Source></BlockInterface><?'
    'xml version="1.0" encoding="utf-16"?><BlockInterface Version="1.0">  <Source Version="1.0" System="T'
    'rue" ClassicSize="0" RetainSize="0" VolatileSize="0" NextFreeLId="11" Library.LStackBitsize="0"><Sec'
    'tion Name="Temp">  <Line LId="9" Name="first_scan" Accessibility="Public" Remanence="Volatile" Symbo'
    'l="Bool" RId="0x2000001" />  <Line LId="10" Name="remanence" Accessibility="Public" Remanence="Volat'
    'ile" Symbol="Bool" RId="0x2000001" /></Section>  </Source></BlockInterface><?xml version="1.0" encod'
    'ing="utf-16"?><BlockInterface Version="1.0">  <Source Version="1.0" ClassicSize="2768" RetainSize="0'
    '" VolatileSize="32" NextFreeLId="128" Library.LStackBitsize="0"><Section Name="Static">  <Line LId="'
    '9" Name="stat_1" Accessibility="Public" Remanence="Volatile" Symbol="Int" Library.Size="16" Library.'
    'Layout.ByteOffset="0" Initial="12" RId="0x2000005" />  <Line LId="10" Name="stat_2" Accessibility="P'
    'ublic" Remanence="Volatile" Symbol="Real" Library.Size="32" Library.Layout.ByteOffset="2" Initial="1'
    '.5" RId="0x2000008" />  <Line LId="11" Name="stat_3" Accessibility="Public" Remanence="Volatile" Sym'
    'bol="Bool" Library.Size="1" Library.Layout.BitOffset="6.0" Initial="" RId="0x2000001" />  <Line LId='
    '"15" Name="stat_4" Accessibility="Public" Remanence="Volatile" Symbol="Time" Library.Size="32" Libra'
    'ry.Layout.ByteOffset="18" RId="0x200000b" />  <Line LId="19" Name="stat_5" Accessibility="Public" Re'
    'manence="Volatile" Symbol="Word" Library.Size="16" Library.Layout.ByteOffset="30" Initial="12" RId="'
    '0x2000004" /></Section>  </Source>  <StartValues><dictionary_entries></dictionary_entries>  </StartV'
    'alues></BlockInterface><?xml version="1.0" encoding="utf-16"?><BlockInterface Version="1.0">  <Sourc'
    'e Version="1.0"><Section Name="Static">  <Line LId="9" Name="COUNT_UP" Symbol="Bool" Library.Size="1'
    '" Library.Layout.BitOffset="0.0" Remanence="Volatile" RId="0x2000001" />  <Line LId="10" Name="COUNT'
    '_DOWN" Symbol="Bool" Library.Size="1" Library.Layout.BitOffset="0.1" Remanence="Volatile" RId="0x200'
    '0001" />  <Line LId="11" Name="RESET" Symbol="Bool" Library.Size="1" Library.Layout.BitOffset="0.2" '
    'Remanence="Volatile" RId="0x2000001" />  <Line LId="12" Name="LOAD" Symbol="Bool" Library.Size="1" L'
    'ibrary.Layout.BitOffset="0.3" Remanence="Volatile" RId="0x2000001" />  <Line LId="13" Name="Q_UP" Sy'
    'mbol="Bool" Library.Size="1" Library.Layout.BitOffset="0.4" Remanence="Volatile" RId="0x2000001" /> '
    ' <Line LId="14" Name="Q_DOWN" Symbol="Bool" Library.Size="1" Library.Layout.BitOffset="0.5" Remanenc'
    'e="Volatile" RId="0x2000001" />  <Line LId="15" Name="PAD" Symbol="Byte" Library.Size="8" Library.La'
    'yout.ByteOffset="1" Remanence="Volatile" RId="0x2000002" />  <Line LId="16" Name="PRESET_VALUE" Symb'
    'ol="Int" Library.Size="16" Library.Layout.ByteOffset="2" Remanence="Volatile" RId="0x2000005" />  <L'
    'ine LId="17" Name="COUNT_VALUE" Symbol="Int" Library.Size="16" Library.Layout.ByteOffset="4" Remanen'
    'ce="Volatile" RId="0x2000005" /></Section>  </Source>  <StartValues><dictionary_entries></dictionary'
    "_entries>  </StartValues></BlockInterface>"
)

# IntfDescTag (90000001) (Adler-32: 0xce9b821b, 1178 bytes)
_DICT_INTFDESCTAG_90000001 = (
    '<IdentContainer>  <Ident Name="Tag_1" Scope="Global" LID="9"><SimpleType>Bool</SimpleType><Access Su'
    'bClass="SimpleAccess">  <SimpleAccess BitNumber="1" ByteNumber="0" Width="Bit" Range="Input" /></Acc'
    'ess>  </Ident>  <Ident Name="Tag_2" Scope="Global" Lid="12"><SimpleType>Int</SimpleType><Access SubC'
    'lass="SimpleAccess">  <SimpleAccess ByteNumber="1" Width="Word" Range="Input" /></Access>  </Ident> '
    ' <Ident Name="Tag_3" Scope="Global" Lid="23"><SimpleType>DInt</SimpleType><Access SubClass="SimpleAc'
    'cess">  <SimpleAccess ByteNumber="2" Width="DWord" Range="Input" /></Access>  </Ident>  <Ident Name='
    '"Tag_4" Scope="Global" Lid="34"><SimpleType>Real</SimpleType><Access SubClass="SimpleAccess">  <Simp'
    'leAccess ByteNumber="3" Width="DWord" Range="Input" /></Access>  </Ident>  <Ident Name="Tag_5" Scope'
    '="Global" Lid="45"><SimpleType>Bool</SimpleType><Access SubClass="SimpleAccess">  <SimpleAccess BitN'
    'umber="4" ByteNumber="4" Width="Bit" Range="Output" /></Access>  </Ident>  <Ident Name="Tag_6" Scope'
    '="Global" Lid="56"><SimpleType>DInt</SimpleType><Access SubClass="SimpleAccess">  <SimpleAccess Byte'
    'Number="5" Width="DWord" Range="Memory" /></Access>  </Ident></IdentContainer>'
)

# LineComm (90000001) (Adler-32: 0x79b2bda3, 534 bytes)
_DICT_LINECOMM_90000001 = (
    '<CommentDictionary><InterfaceLineComments><Comment UId="1" LineId="3"><DictEntry Language="en-US">th'
    'is is a the in to an can be for are network and</DictEntry> </Comment><Comment UId="0" LineId="2"><D'
    'ictEntry Language="en-US">dies ist ein der die das im nach einen kann sein für sind Netzwerk und</Di'
    "ctEntry> </Comment></InterfaceLineComments><BodyLineComments /> </CommentDictionary><CommentDictiona"
    "ry><InterfaceLineComments /><BodyLineComments /></CommentDictionary><CommentDictionary><InterfaceLin"
    "eComments /> </CommentDictionary>"
)

# LineComm (98000001) (Adler-32: 0x3c55436a, 206 bytes)
_DICT_LINECOMM_98000001 = (
    'UId=" RefID="<Part>51:52:53:54:55<BodyLineComments><CommentDictionary><InterfaceLineComments<Part Ve'
    'rsion="2.0" ID=" Kind=" ParentID="<CommentCommentID=" Path=" fr-FRit-IT<DictEntry Language="de-DE"en'
    '-US=">'
)

# NWC (90000001) (Adler-32: 0xab6fa31e, 463 bytes)
_DICT_NWC_90000001 = (
    '<CommentDictionary><NetworkComments><Comment RefID="2"><DictEntry Language="en-US"></DictEntry></Com'
    'ment><Comment RefID="16"><DictEntry Language="en-US">this is a the in to an can be for are network a'
    'nd</DictEntry></Comment><Comment RefID="26"><DictEntry Language="en-US">dies ist ein der die das im '
    "nach einen kann sein für sind Netzwerk und</DictEntry></Comment></NetworkComments></CommentDictionar"
    "y><CommentDictionary>  <NetworkComments /></CommentDictionary>"
)

# NWC (98000001) (Adler-32: 0xc5d26ac3, 301 bytes)
_DICT_NWC_98000001 = (
    "this is a the in to an can be for are network and dies ist ein der die das im nach einen kann sein f"
    'ür sind Netzwerk und<CommentDictionary><NetworkComments><Comment RefID="2"><DictEntry Language="en-U'
    'S"de-DE"it-IT"fr-FR"></DictEntry></Comment></NetworkComments></CommentDictionary><NetworkComments />'
)

# NWT (90000001) (Adler-32: 0xfd69ac74, 503 bytes)
_DICT_NWT_90000001 = (
    '<CommentDictionary><NetworkTitles></Comment>    <Comment RefID="0">  <DictEntry Language="en-US"> "M'
    'ain Program Sweep (Cycle)"</DictEntry></Comment><Comment RefID="2"><DictEntry Language="en-US"></Dic'
    'tEntry></Comment><Comment RefID="16"><DictEntry Language="en-US">this is a the in to an can be for a'
    're network and</DictEntry></Comment><Comment RefID="26"><DictEntry Language="en-US">dies ist ein der'
    " die das im nach einen kann sein für sind Netzwerk und</DictEntry></NetworkTitles></CommentDictionar"
    "y>"
)

# NWT (98000001) (Adler-32: 0x845fc605, 571 bytes)
_DICT_NWT_98000001 = (
    '<CommentDictionary><NetworkTitles><Comment<DictEntry RefID=" Language="="><CommentDictionary><Networ'
    'kTitles></Comment><Comment RefID="0"><DictEntry Language="de-DE"> "Main Program Sweep (Cycle)"</Dict'
    'Entry></Comment><Comment RefID="2"><DictEntry Language="fr-FR"></DictEntry></Comment><Comment RefID='
    '"16"><DictEntry Language="it-IT">this is a the in to an can be for are network and</DictEntry></Comm'
    'ent><Comment RefID="26"><DictEntry Language="en-US">dies ist ein der die das im nach einen kann sein'
    " für sind Netzwerk und</DictEntry></NetworkTitles></CommentDictionary>"
)

# TagLineComm (90000001) (Adler-32: 0xe2729ea1, 455 bytes)
_DICT_TAGLINECOMM_90000001 = (
    '<CommentDictionary><TagLineComments><Comment RefID="1"><DictEntry Language="en-US" /> </Comment><Com'
    'ment RefID="11"><DictEntry Language="en-US">this is a the in to an can be for are network and</DictE'
    'ntry></Comment><Comment RefID="111"><DictEntry Language="en-US">dies ist ein der die das im nach ein'
    "en kann sein für sind Netzwerk und</DictEntry></Comment></TagLineComments></CommentDictionary><Comme"
    "ntDictionary>  <TagLineComments /></CommentDictionary>"
)


ZLIB_DICTIONARIES: dict[int, bytes] = {
    0xEFAEAE49: _DICT_BODYDESC_90000001.encode("utf-8"),
    0x1398A37F: _DICT_COMPILERSETTINGS_90000001.encode("utf-8"),
    0x1BAC39F0: _DICT_DEBUGINFO_90000001.encode("utf-8"),
    0x66052B13: _DICT_DEBUGINFO_INTFDESC_98000001.encode("utf-8"),
    0x9B6A3A92: _DICT_EXTREFDATA_90000001.encode("utf-8"),
    0xDF91B6BB: _DICT_IDENTES_90000001.encode("utf-8"),
    0x81D8DB20: _DICT_IDENTES_90000002.encode("utf-8"),
    0x5814B03B: _DICT_IDENTES_98000001.encode("utf-8"),
    0xDA4A88F4: _DICT_INTREFDATA_90000001.encode("utf-8"),
    0xB0155FF8: _DICT_INTREFDATA_98000001.encode("utf-8"),
    0x4B8416F0: _DICT_INTFDESC_90000001.encode("utf-8"),
    0xCE9B821B: _DICT_INTFDESCTAG_90000001.encode("utf-8"),
    0x79B2BDA3: _DICT_LINECOMM_90000001.encode("utf-8"),
    0x3C55436A: _DICT_LINECOMM_98000001.encode("utf-8"),
    0xAB6FA31E: _DICT_NWC_90000001.encode("utf-8"),
    0xC5D26AC3: _DICT_NWC_98000001.encode("utf-8"),
    0xFD69AC74: _DICT_NWT_90000001.encode("utf-8"),
    0x845FC605: _DICT_NWT_98000001.encode("utf-8"),
    0xE2729EA1: _DICT_TAGLINECOMM_90000001.encode("utf-8"),
}

ZLIB_DICT_NAMES: dict[int, str] = {
    0xEFAEAE49: "BodyDesc (90000001)",
    0x1398A37F: "CompilerSettings (90000001)",
    0x1BAC39F0: "DebugInfo (90000001)",
    0x66052B13: "DebugInfo_IntfDesc (98000001)",
    0x9B6A3A92: "ExtRefData (90000001)",
    0xDF91B6BB: "IdentES (90000001)",
    0x81D8DB20: "IdentES (90000002)",
    0x5814B03B: "IdentES (98000001)",
    0xDA4A88F4: "IntRefData (90000001)",
    0xB0155FF8: "IntRefData (98000001)",
    0x4B8416F0: "IntfDesc (90000001)",
    0xCE9B821B: "IntfDescTag (90000001)",
    0x79B2BDA3: "LineComm (90000001)",
    0x3C55436A: "LineComm (98000001)",
    0xAB6FA31E: "NWC (90000001)",
    0xC5D26AC3: "NWC (98000001)",
    0xFD69AC74: "NWT (90000001)",
    0x845FC605: "NWT (98000001)",
    0xE2729EA1: "TagLineComm (90000001)",
}
