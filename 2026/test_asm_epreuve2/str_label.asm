_before1:
    STR R0 R1 _after1
_before2:
    STR R1 R2 _after2
_after1:
    STR R2 R3 _before2
_after2:
    STR R3 R0 _before1
