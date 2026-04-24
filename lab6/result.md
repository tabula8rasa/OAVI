# Лабораторная работа №6. Сегментация текста

**Алфавит:** кириллица заглавная  
**Исходное изображение:** `phrase.bmp`

---

## Используемые методы

Изображение загружается как монохромное: чёрный пиксель принимается за 1, белый пиксель — за 0.

Для выделения строк строится горизонтальный профиль изображения: сумма чёрных пикселей по каждой строке `Y`.

Для выделения символов внутри каждой строки строится косой вертикальный профиль. Он нужен для наклонного шрифта: пиксельные строки сдвигаются, после чего символы лучше разделяются по вертикальным проекциям.

Сегментация выполняется по профилям с прореживанием: разрез допускается не только при нулевом профиле, но и при малых значениях профиля.

---

## 1. Исходное изображение

![](./result/phrase_source.bmp)

---

## 2. Горизонтальный профиль и выделение строк

![](./result/horizontal_profile.png)

| № строки | Начало Y | Конец Y | Высота |
|---:|---:|---:|---:|
| 1 | 2 | 142 | 141 |
| 2 | 202 | 286 | 85 |
| 3 | 377 | 487 | 111 |
| 4 | 553 | 663 | 111 |

---

## 3. Косые вертикальные профили строк

### Строка 1

![](./result/line_1.bmp)

![](./result/profiles/vertical_profile_line_1.png)

### Строка 2

![](./result/line_2.bmp)

![](./result/profiles/vertical_profile_line_2.png)

### Строка 3

![](./result/line_3.bmp)

![](./result/profiles/vertical_profile_line_3.png)

### Строка 4

![](./result/line_4.bmp)

![](./result/profiles/vertical_profile_line_4.png)

---

## 4. Результат сегментации символов

![](./result/segmented_boxes.png)

Координаты обрамляющих прямоугольников упорядочены в порядке чтения: слева направо, сверху вниз.

| № | x1 | y1 | x2 | y2 | Ширина | Высота |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2 | 27 | 62 | 109 | 61 | 83 |
| 2 | 72 | 25 | 135 | 109 | 64 | 85 |
| 3 | 141 | 27 | 208 | 109 | 68 | 83 |
| 4 | 217 | 27 | 287 | 109 | 71 | 83 |
| 5 | 325 | 27 | 397 | 109 | 73 | 83 |
| 6 | 408 | 25 | 476 | 111 | 69 | 87 |
| 7 | 479 | 25 | 554 | 109 | 76 | 85 |
| 8 | 556 | 25 | 625 | 111 | 70 | 87 |
| 9 | 629 | 25 | 733 | 109 | 105 | 85 |
| 10 | 770 | 27 | 842 | 109 | 73 | 83 |
| 11 | 850 | 27 | 917 | 109 | 68 | 83 |
| 12 | 954 | 27 | 1060 | 109 | 107 | 83 |
| 13 | 1063 | 25 | 1210 | 142 | 148 | 118 |
| 14 | 1223 | 25 | 1289 | 111 | 67 | 87 |
| 15 | 1299 | 2 | 1371 | 109 | 73 | 108 |
| 16 | 3 | 202 | 75 | 286 | 73 | 85 |
| 17 | 83 | 203 | 155 | 285 | 73 | 83 |
| 18 | 164 | 203 | 230 | 285 | 67 | 83 |
| 19 | 237 | 203 | 304 | 285 | 68 | 83 |
| 20 | 312 | 203 | 378 | 285 | 67 | 83 |
| 21 | 385 | 203 | 452 | 285 | 68 | 83 |
| 22 | 458 | 203 | 524 | 285 | 67 | 83 |
| 23 | 1 | 377 | 61 | 460 | 61 | 84 |
| 24 | 74 | 377 | 143 | 462 | 70 | 86 |
| 25 | 154 | 377 | 226 | 462 | 73 | 86 |
| 26 | 232 | 377 | 307 | 460 | 76 | 84 |
| 27 | 315 | 378 | 387 | 460 | 73 | 83 |
| 28 | 397 | 378 | 501 | 487 | 105 | 110 |
| 29 | 509 | 378 | 576 | 460 | 68 | 83 |
| 30 | 586 | 377 | 653 | 462 | 68 | 86 |
| 31 | 662 | 378 | 766 | 460 | 105 | 83 |
| 32 | 776 | 378 | 837 | 460 | 62 | 83 |
| 33 | 847 | 377 | 918 | 462 | 72 | 86 |
| 34 | 924 | 378 | 992 | 460 | 69 | 83 |
| 35 | 1030 | 378 | 1096 | 460 | 67 | 83 |
| 36 | 2 | 554 | 75 | 636 | 74 | 83 |
| 37 | 86 | 553 | 154 | 638 | 69 | 86 |
| 38 | 157 | 554 | 237 | 636 | 81 | 83 |
| 39 | 240 | 553 | 309 | 638 | 70 | 86 |
| 40 | 315 | 554 | 421 | 636 | 107 | 83 |
| 41 | 459 | 554 | 532 | 636 | 74 | 83 |
| 42 | 541 | 554 | 645 | 663 | 105 | 110 |
| 43 | 656 | 553 | 723 | 638 | 68 | 86 |
| 44 | 732 | 554 | 836 | 636 | 105 | 83 |
| 45 | 846 | 554 | 908 | 636 | 63 | 83 |
| 46 | 945 | 553 | 1004 | 636 | 60 | 84 |
| 47 | 1016 | 554 | 1078 | 636 | 63 | 83 |
| 48 | 1084 | 554 | 1113 | 636 | 30 | 83 |
| 49 | 1121 | 553 | 1196 | 636 | 76 | 84 |
| 50 | 1198 | 553 | 1342 | 656 | 145 | 104 |

---

## 5. Вырезанные символы и их профили

### Символ 1

![](./result/symbols/symbol_01.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_01_profile_x.png) | ![](./result/profiles/symbol_01_profile_y.png) |

### Символ 2

![](./result/symbols/symbol_02.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_02_profile_x.png) | ![](./result/profiles/symbol_02_profile_y.png) |

### Символ 3

![](./result/symbols/symbol_03.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_03_profile_x.png) | ![](./result/profiles/symbol_03_profile_y.png) |

### Символ 4

![](./result/symbols/symbol_04.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_04_profile_x.png) | ![](./result/profiles/symbol_04_profile_y.png) |

### Символ 5

![](./result/symbols/symbol_05.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_05_profile_x.png) | ![](./result/profiles/symbol_05_profile_y.png) |

### Символ 6

![](./result/symbols/symbol_06.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_06_profile_x.png) | ![](./result/profiles/symbol_06_profile_y.png) |

### Символ 7

![](./result/symbols/symbol_07.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_07_profile_x.png) | ![](./result/profiles/symbol_07_profile_y.png) |

### Символ 8

![](./result/symbols/symbol_08.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_08_profile_x.png) | ![](./result/profiles/symbol_08_profile_y.png) |

### Символ 9

![](./result/symbols/symbol_09.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_09_profile_x.png) | ![](./result/profiles/symbol_09_profile_y.png) |

### Символ 10

![](./result/symbols/symbol_10.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_10_profile_x.png) | ![](./result/profiles/symbol_10_profile_y.png) |

### Символ 11

![](./result/symbols/symbol_11.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_11_profile_x.png) | ![](./result/profiles/symbol_11_profile_y.png) |

### Символ 12

![](./result/symbols/symbol_12.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_12_profile_x.png) | ![](./result/profiles/symbol_12_profile_y.png) |

### Символ 13

![](./result/symbols/symbol_13.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_13_profile_x.png) | ![](./result/profiles/symbol_13_profile_y.png) |

### Символ 14

![](./result/symbols/symbol_14.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_14_profile_x.png) | ![](./result/profiles/symbol_14_profile_y.png) |

### Символ 15

![](./result/symbols/symbol_15.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_15_profile_x.png) | ![](./result/profiles/symbol_15_profile_y.png) |

### Символ 16

![](./result/symbols/symbol_16.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_16_profile_x.png) | ![](./result/profiles/symbol_16_profile_y.png) |

### Символ 17

![](./result/symbols/symbol_17.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_17_profile_x.png) | ![](./result/profiles/symbol_17_profile_y.png) |

### Символ 18

![](./result/symbols/symbol_18.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_18_profile_x.png) | ![](./result/profiles/symbol_18_profile_y.png) |

### Символ 19

![](./result/symbols/symbol_19.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_19_profile_x.png) | ![](./result/profiles/symbol_19_profile_y.png) |

### Символ 20

![](./result/symbols/symbol_20.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_20_profile_x.png) | ![](./result/profiles/symbol_20_profile_y.png) |

### Символ 21

![](./result/symbols/symbol_21.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_21_profile_x.png) | ![](./result/profiles/symbol_21_profile_y.png) |

### Символ 22

![](./result/symbols/symbol_22.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_22_profile_x.png) | ![](./result/profiles/symbol_22_profile_y.png) |

### Символ 23

![](./result/symbols/symbol_23.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_23_profile_x.png) | ![](./result/profiles/symbol_23_profile_y.png) |

### Символ 24

![](./result/symbols/symbol_24.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_24_profile_x.png) | ![](./result/profiles/symbol_24_profile_y.png) |

### Символ 25

![](./result/symbols/symbol_25.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_25_profile_x.png) | ![](./result/profiles/symbol_25_profile_y.png) |

### Символ 26

![](./result/symbols/symbol_26.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_26_profile_x.png) | ![](./result/profiles/symbol_26_profile_y.png) |

### Символ 27

![](./result/symbols/symbol_27.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_27_profile_x.png) | ![](./result/profiles/symbol_27_profile_y.png) |

### Символ 28

![](./result/symbols/symbol_28.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_28_profile_x.png) | ![](./result/profiles/symbol_28_profile_y.png) |

### Символ 29

![](./result/symbols/symbol_29.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_29_profile_x.png) | ![](./result/profiles/symbol_29_profile_y.png) |

### Символ 30

![](./result/symbols/symbol_30.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_30_profile_x.png) | ![](./result/profiles/symbol_30_profile_y.png) |

### Символ 31

![](./result/symbols/symbol_31.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_31_profile_x.png) | ![](./result/profiles/symbol_31_profile_y.png) |

### Символ 32

![](./result/symbols/symbol_32.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_32_profile_x.png) | ![](./result/profiles/symbol_32_profile_y.png) |

### Символ 33

![](./result/symbols/symbol_33.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_33_profile_x.png) | ![](./result/profiles/symbol_33_profile_y.png) |

### Символ 34

![](./result/symbols/symbol_34.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_34_profile_x.png) | ![](./result/profiles/symbol_34_profile_y.png) |

### Символ 35

![](./result/symbols/symbol_35.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_35_profile_x.png) | ![](./result/profiles/symbol_35_profile_y.png) |

### Символ 36

![](./result/symbols/symbol_36.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_36_profile_x.png) | ![](./result/profiles/symbol_36_profile_y.png) |

### Символ 37

![](./result/symbols/symbol_37.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_37_profile_x.png) | ![](./result/profiles/symbol_37_profile_y.png) |

### Символ 38

![](./result/symbols/symbol_38.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_38_profile_x.png) | ![](./result/profiles/symbol_38_profile_y.png) |

### Символ 39

![](./result/symbols/symbol_39.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_39_profile_x.png) | ![](./result/profiles/symbol_39_profile_y.png) |

### Символ 40

![](./result/symbols/symbol_40.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_40_profile_x.png) | ![](./result/profiles/symbol_40_profile_y.png) |

### Символ 41

![](./result/symbols/symbol_41.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_41_profile_x.png) | ![](./result/profiles/symbol_41_profile_y.png) |

### Символ 42

![](./result/symbols/symbol_42.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_42_profile_x.png) | ![](./result/profiles/symbol_42_profile_y.png) |

### Символ 43

![](./result/symbols/symbol_43.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_43_profile_x.png) | ![](./result/profiles/symbol_43_profile_y.png) |

### Символ 44

![](./result/symbols/symbol_44.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_44_profile_x.png) | ![](./result/profiles/symbol_44_profile_y.png) |

### Символ 45

![](./result/symbols/symbol_45.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_45_profile_x.png) | ![](./result/profiles/symbol_45_profile_y.png) |

### Символ 46

![](./result/symbols/symbol_46.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_46_profile_x.png) | ![](./result/profiles/symbol_46_profile_y.png) |

### Символ 47

![](./result/symbols/symbol_47.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_47_profile_x.png) | ![](./result/profiles/symbol_47_profile_y.png) |

### Символ 48

![](./result/symbols/symbol_48.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_48_profile_x.png) | ![](./result/profiles/symbol_48_profile_y.png) |

### Символ 49

![](./result/symbols/symbol_49.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_49_profile_x.png) | ![](./result/profiles/symbol_49_profile_y.png) |

### Символ 50

![](./result/symbols/symbol_50.bmp)

| Профиль X | Профиль Y |
|:---:|:---:|
| ![](./result/profiles/symbol_50_profile_x.png) | ![](./result/profiles/symbol_50_profile_y.png) |
