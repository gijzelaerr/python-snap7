import re


def fromTIAtoSnap(file_path:str):
    """function to convert TIA export layout to Snap7 DB input layout
    """
    # Stringa di esempio
    stringa =  open(file_path, 'r').read()

    # Espressione regolare per isolare i primi tre valori separati da tabulazioni
    pattern = r'^[\t]*([^\t]+)\t([^\t]+)\t([^\t]+)'

    # Suddividi la stringa in righe
    righe = stringa.strip().split('\n')

    newText : str = ""
    # Itera su ogni riga e cerca la corrispondenza
    for riga in righe:
        match = re.match(pattern, riga)
        print(f"Riga:\t{riga}")
        if match:
            var_name, type_, index = match.groups()

            print(f"var:\t{var_name.strip()}")
            print(f"type:\t{type_.strip()}")
            print(f"index:\t{index.strip()}")
            newText = newText+" "+index+" "+var_name+" "+type_+"\n"
            
        else:
            print("error with parse")
            #print(f"Nessuna corrispondenza trovata nella riga: {riga}")
        print("parsing completed")
    return newText



if __name__ == "__main__":
    from snap7 import DB

    file_path = r"example\db_layout_fromTIA.txt"

    dbSpecificationLayout = fromTIAtoSnap(file_path)

    print(dbSpecificationLayout)
    db_ = DB(
        1,
        bytearray(1),
        dbSpecificationLayout,
        1,
        1,

    )

    # with open("Output.txt", "w") as text_file:
    #     text_file.write(dbSpecificationLayout)