_before1:
    LDR R0 R1 _after1
_before2:
    LDR R1 R2 _after2
_after1:
    LDR R2 R3 _before2
_after2:
    LDR R3 R0 _before1
