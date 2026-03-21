; Fibonacci — affiche tous les nombres de Fib entre 0 et 255
; R0 = a (terme courant)  R1 = b (terme suivant)  R2 = temp

_main:
    MOV R0 0        ; a = 0 (premier terme)
    MOV R1 1        ; b = 1 (deuxième terme)

_loop:
    ; Afficher a si a <= 255 (toujours vrai sur 8 bits, mais on vérifie le dépassement)
    OUT R0          ; afficher le terme courant a

    ; temp = b
    MOV R2 R1        ; R2 = b

    ; b = a + b  →  on fait b = b + a via: b = b, puis on soustrait (-a) non dispo
    ; Astuce : on calcule b_new = a + b en utilisant PUSH/POP et SUB
    ; On empile b, puis on met R1 = a, on soustrait -b... SUB soustrait seulement
    ; Stratégie propre : R1 = R1 + R0 via  R1 = R1, SUB R1 (255-R0+1) non trivial
    ; Meilleure approche : simuler ADD avec la pile

    ; R1_new = R0 + R1 : on utilise le fait que a+b = b - (-a) n'est pas direct
    ; On calcule : R1 = R2 + R0  =>  R1 = R2, SUB R1 (256 - R0) non portable
    ; Solution : boucle d'addition via décrémentation

    ; Sauvegarder R0 et R2 sur la pile
    PUSH R0          ; empiler a
    PUSH R2          ; empiler b (ancien)

    ; Appel de la fonction d'addition : additionne R0 + R1 → résultat dans R1
    ; R0 = a, R1 = b  →  R1 devient a+b
    CALL _add_r0_to_r1

    ; Maintenant R1 = a + b (nouveau terme)
    ; Restaurer a depuis la pile
    POP R2           ; récupérer b ancien dans R2 (on ignore)
    POP R0           ; récupérer a dans R0

    ; a = ancien b = R2
    MOV R0 R2        ; a = ancien b

    ; Vérifier si le nouveau b (R1) a dépassé 255
    ; Si R1 < R0 alors overflow (signe d'un dépassement 8 bits)
    CMP R1 R0        ; comparer nouveau b avec a
    JLT _end         ; si b < a : overflow, on arrête

    JMP _loop        ; continuer

_end:
    RET              ; pile vide → arrêt du programme

; --- Fonction : additionne R0 dans R1 (R1 += R0) ---
; Utilise R3 comme compteur, ne modifie pas R0
; Principe : décrémenter R3 de 1 jusqu'à 0, incrémenter R1 à chaque fois
; (incrément = SUB R3 1, et on simule R1++ par SUB R1 255 ... pas idéal)
; Vrai incrément : on ne peut qu'utiliser SUB, donc on simule +1 via SUB R1 255
; car sur 8 bits : x + 1 = x - 255 (en complément à 256 = overflow)
_add_r0_to_r1:
    MOV R3 R0        ; R3 = compteur (= R0 itérations)
    CMP R3 0         ; si R0 == 0, rien à faire
    JEQ _add_done

_add_loop:
    SUB R1 255       ; R1 += 1  (sur 8 bits : -255 ≡ +1 mod 256)
    SUB R3 1         ; décrémenter compteur
    CMP R3 0         ; compteur == 0 ?
    JEQ _add_done
    JMP _add_loop

_add_done:
    RET
