_before1:
	CALL _after1
	RET
_before2:
	CALL _after2
	RET
_after1:
	CALL _before2
	RET
_after2:
	CALL _before1
	RET
