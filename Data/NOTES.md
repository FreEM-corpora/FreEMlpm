# Notes NER

Contrôler tous les mots répétés en majuscule:
```console
^([A-Z]{2,})\t.*\n\1\t.*
```

Contrôler les lieux suivants:
```console
Asie
Guinée
```

Et les mots suivants:
```console
général	général	Nc
président	président	Nc
lieutenant	lieutenant	Nc
préfecture	préfecture	Nc	
```

Contrôler si fort=qualifier ou kind? avec regex ville\tNc\tB
```console
ville	ville	Nc	B-loc	B-loc.adm.town	B-comp.kind	O	_
forte	fort	Ag	I-loc	I-loc.adm.town	I-comp.kind	O	
```

Contrôler les apostrophes:
```console
d’acheter	d’acheter	Vvn	O	O	O	O	_
```

et les cotes:
```console
côte	côte	Nc	////
```

Ajouter les ordonnances suivi d'une personne (_Ordonnance de Louis XIV_)
```console
ordonnance	ordonnance	Nc	O	O	O	O	_
de	de	S	O	O	O	O	_
François	François	Np	B-pers	B-pers.ind	B-comp.name	O	Q132548
II	2	Mc	I-pers	I-pers.ind	B-comp.qualifier	O	Q132548
```

Type:
```console
ordonnance	ordonnance	Nc	B-prod	B-prod.rule	B-comp.kind	O	_
du	de_le	S+Da	I-prod	I-prod.rule	O	O	_

ordonnance	ordonnance	Nc	B-prod	B-prod.rule	B-comp.kind	O	_
de	de	S	I-prod	I-prod.rule	O	O	_
Clidaman	Clidaman	Np	I-prod	I-prod.rule	B-comp.name	O	_
```

Les états. Chercher:
```console
états	état	Nc	O	O	O	O	_
d
```

Type:
```console
états	état	Nc	B-org	B-org.adm	B-comp.kind	O	_
de	de	S	I-org	I-org.adm	O	O	_
Gènes	Gênes	Np	I-org	I-org.adm	B-comp.name	B-loc.adm.town	_
```
Recontrôler tous les _saint_ (Saint-Denis, etc.)
```console
s'	se	Pp	O	O	O	O	_
emparèrent	emparer	Vvc	O	O	O	O	_
de	de	S	O	O	O	O	_
Sainte	Sainte	Np	B-pers	B-pers.ind	O	O	_
-	-	Fo	I-pers	I-pers.ind	O	O	_
Catherine	Catherine	Np	I-pers	I-pers.ind	O	O	_
```
guere	guère	Rn	O	O	O	O	_


Contrôler:
```console
aux	à_le	S+Da	O	O	O	O	_
confins	confin	Nc	B-loc	B-loc	O	O	_
du	de_le	S+Da	I-loc	I-loc	O	O	_
comté	comté	Nc	I-loc	I-loc	O	O	_
de	de	S	I-loc	I-loc	O	O	_
Nice	Nice	Np	I-loc	I-loc	O	B-loc.adm.town	_

grande	grand	Ag	O	O	O	O	_
Asie	Asie	Np	B-loc	B-loc.adm.sup	O	O	Q48

pays	pays	Nc	O	O	O	O	_
des	de_le	S+Da	O	O	O	O	_
malabares	malabares	Nc	O	O	O	O	_

montagnes	montagne	Nc	O	O	O	O	_
des	de_le	S+Da	O	O	O	O	_
hollandais	hollandais	Nc	O	O	O	O	_

terre	terre	Nc	O	O	O	O	_
de	de	S	O	O	O	O	_
la	le	Da	O	O	O	O	_
compagnie	compagnie	Nc	O	O	O	O	_

mission	mission	Nc	O	O	O	O	_
de	de	S	O	O	O	O	_
saint	saint	Np	B-pers	B-pers.ind	O	O	_
-	-	Fo	I-pers	I-pers.ind	O	O	_
Charles	Charles	Np	I-pers	I-pers.ind	O	O	_

garde	garde	Nc	O	O	O	O	_
des	de_le	S+Da	O	O	O	O	_
seaux	seau	Nc	O	O	O	O	_
du	de_le	S+Da	O	O	O	O	_
Vair	vair	Np	B-pers	B-pers.ind	O	O	_

île	île	Nc	B-loc	B-loc.phys.geo	B-comp.kind	O	_
de	de	S	I-loc	I-loc.phys.geo	O	O	_
l'	le	Da	I-loc	I-loc.phys.geo	O	O	_
Amérique	Amérique	Np	I-loc	I-loc.phys.geo	B-comp.name	B-loc.adm.sup	_
septentrionale	septentrionale	Nc	I-loc	I-loc.phys.geo	B-comp.qualifier	O	Q49

don	don	Nc	B-pers	B-pers.ind	B-comp.title	O	_
Philippe	Philippe	Np	I-pers	I-pers.ind	B-comp.name	O	_
des	de_le	S+Da	I-pers	I-pers.ind	I-comp.name	O	_
Marays	marays	Np	I-pers	I-pers.ind	I-comp.name	O	_
Viceroy	viceroi	Nc	I-pers	I-pers.ind	B-comp.title	O	_
de	de	S	I-pers	I-pers.ind	I-comp.title	O	_
Papeligosse	papeligosse	Np	BI-pers	I-pers.ind	I-comp.title	O	_

Gui	Gui	Np	B-pers	B-pers.ind	O	O	_
d'	de	S	I-pers	I-pers.ind	O	O	_
Athies	Athies	Np	I-pers	I-pers.ind	O	O	_
vice	vice	Nc	O	O	O	O	_
-	-	Fo	O	O	O	O	_
chancelier	chancelier	Nc	O	O	O	O	_
```

Eviter les cas à rallonge:
```console
Philippe	Philippe	Np	B-pers	B-pers.ind	O	O	_
Huraut	Huraut	Np	I-pers	I-pers.ind	O	O	_
,	,	Fw	O	O	O	O	_
comte	comte	Nc	B-func	B-func.ind	B-comp.kind	O	_
de	de	S	I-func	I-func.ind	O	O	_
Chiverny	Chiverny	Np	I-func	I-func.ind	B-comp.name	O	_
,	,	Fw	O	O	O	O	_
commandeur	commandeur	Nc	B-func	B-func.ind	O	O	_
de	de	S	I-func	I-func.ind	O	O	_
l'	le	Da	I-func	I-func.ind	O	O	_
ordre	ordre	Nc	I-func	I-func.ind	O	O	_
du	de_le	S+Da	I-func	I-func.ind	O	O	_
S.	saint	Xa	I-func	I-func.ind	O	O	_
Esprit	esprit	Nc	I-func	I-func.ind	O	O	_

Fréderic	Frédéric	Np	B-pers	B-pers.ind	B-comp.name	O	_
III	3	Mc	I-pers	I-pers.ind	B-comp.qualifier	O	_
empereur	empereur	Nc	O	O	O	O	_
pieux	pieux	Ag	O	O	O	O	_
,	,	Fw	O	O	O	O	_
auguste	auguste	Ag	O	O	O	O	_
,	,	Fw	O	O	O	O	_
souverain	souverain	Ag	O	O	O	O	_
de	de	S	O	O	O	O	_
la	le	Da	O	O	O	O	_
chrêtienté	chrétienté	Nc	O	O	O	O	_
,	,	Fw	O	O	O	O	_
roi	roi	Nc	B-func	B-func.ind	B-comp.kind	O	_
de	de	S	I-func	I-func.ind	O	O	_
Hongrie	Hongrie	Np	I-func	I-func.ind	B-comp.name	B-loc.adm.nat	_
,	,	Fw	O	O	O	O	_
de	de	S	O	O	O	O	_
Dalmatie	Dalmatie	Np	B-loc	B-loc.adm.reg	O	O	Q528042
,	,	Fw	O	O	O	O	_
de	de	S	O	O	O	O	_
Croatie	Croatie	Np	B-loc	B-loc.adm.town	O	O	Q224
,	,	Fw	O	O	O	O	_
archiduc	archiduc	Nc	B-func	B-func.ind	B-comp.kind	O	_
d'	de	S	I-func	I-func.ind	O	O	_
Autriche	Autriche	Np	I-func	I-func.ind	B-comp.name	B-loc.adm.nat	_
etc.	etc	Xa	O	O	O	O	_
elle	il	Pp	O	O	O	O	_

Meric	Méry	Np	B-pers	B-pers.ind	O	O	_
de	de	S	I-pers	I-pers.ind	O	O	_
Vic	Vic	Np	I-pers	I-pers.ind	O	O	_
,	,	Fw	O	O	O	O	_
Seigneur	seigneur	Nc	B-func	B-func.ind	B-comp.kind	O	_
d'	de	S	I-func	I-func.ind	O	O	_
Ermenonville	Ermenonville	Np	I-func	I-func.ind	B-comp.name	O	_
,	,	Fw	O	O	O	O	_
conseiller	conseiller	Nc	O	O	O	O	_
d'	de	S	O	O	O	O	_
état	état	Nc	O	O	O	O	_
,	,	Fw	O	O	O	O	_
&	et	Cc	O	O	O	O	_
intendant	intendant	Nc	O	O	O	O	_
de	de	S	O	O	O	O	_
justice	justice	Nc	O	O	O	O	_
en	en	S	O	O	O	O	_
Guienne	Guyenne	Np	B-loc	B-loc.adm.reg	O	O	Q849324
```

Ce qui pose des problèmes du type:
```console
coûtumes	coutume	Nc	B-prod	B-prod.rule	B-comp.kind	O	_
de	de	S	I-prod	I-prod.rule	O	O	_
Vitry	Vitry	Np	I-prod	I-prod.rule	B-comp.name	O	_
,	,	Fw	O	O	O	O	_
Sens	Sens	Np	B-loc	B-loc.adm.town	O	O	Q212420
,	,	Fw	O	O	O	O	_
Haynault	Hainaut	Np	B-loc	B-loc.adm.reg	O	O	Q11296806
```

Exemple de cas limite:
```console
Roger	Roger	Np	B-pers	B-pers.ind	B-comp.name	O	_
vice	vice	Nc	B-pers	B-pers.ind	B-comp.title	O	_
-	-	Fo	I-pers	I-pers.ind	I-comp.title	O	_
chancelier	chancelier	Nc	I-pers	I-pers.ind	I-comp.title	O	_
de	de	S	I-pers	I-pers.ind	I-comp.title	O	_
Richard	Richard	Np	I-pers	I-pers.ind	I-comp.title	O	_
I	1	Mc	I-pers	I-pers.ind	I-comp.title	O	_
.	.	Fo	O	O	O	O	_
roi	roi	Nc	B-func	B-func.ind	B-comp.kind	O	_
d'	de	S	I-func	I-func.ind	O	O	_
Angleterre	Angleterre	Np	I-func	I-func.ind	B-comp.name	B-loc.adm.nat	_
```
