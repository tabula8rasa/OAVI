# Лабораторная работа №4. Выделение контуров на изображении

**Вариант:** 4
**Метод:** Оператор Собеля 3×3

---

## Используемые методы

### Преобразование в полутон
Исходные цветные изображения переводятся в полутоновые по формуле взвешенного усреднения:

$$
Y = 0.299 \cdot R + 0.587 \cdot G + 0.114 \cdot B
$$

### Оператор Собеля 3×3
Ядра для вычисления горизонтальной и вертикальной составляющих градиента:

$$
G_x = \begin{bmatrix}
-1 & 0 & 1 \\
-2 & 0 & 2 \\
-1 & 0 & 1
\end{bmatrix}, \quad
G_y = \begin{bmatrix}
1 & 2 & 1 \\
0 & 0 & 0 \\
-1 & -2 & -1
\end{bmatrix}
$$

Модуль градиента вычисляется как сумма модулей:

$$
|G| = |G_x| + |G_y|
$$

### Нормализация
Каждая градиентная матрица линейно растягивается в диапазон [0, 255] для визуализации.

### Бинаризация
Для выделения контуров применяется пороговая обработка: пиксели со значением выше порога становятся белыми, остальные — чёрными. Для каждого изображения приведены результаты бинаризации при порогах 10, 20, 30, 40, 50, 60, 70.

---

## Результаты

### 1. Исходные и полутоновые изображения

| № | Исходное (цветное) | Полутоновое |
|---|--------------------|-------------|
| **text1** | ![text1](./result/text1/text1_original.png) | ![text1_gray](./result/text1/text1_gray.png) |
| **text2** | ![text2](./result/text2/text2_original.png) | ![text2_gray](./result/text2/text2_gray.png) |
| **text3** | ![text3](./result/text3/text3_original.png) | ![text3_gray](./result/text3/text3_gray.png) |
| **text4** | ![text4](./result/text4/text4_original.png) | ![text4_gray](./result/text4/text4_gray.png) |
| **text5** | ![text5](./result/text5/text5_original.png) | ![text5_gray](./result/text5/text5_gray.png) |

---

### 2. Градиентные матрицы $G_x$, $G_y$ и модуль градиента $G$ (нормализованные)

#### text1
| $G_x$ | $G_y$ | $G$ |
|---------|---------|-------|
| ![text1_Gx](./result/text1/text1_Gx.png) | ![text1_Gy](./result/text1/text1_Gy.png) | ![text1_G](./result/text1/text1_G.png) |

#### text2
| $G_x$ | $G_y$ | $G$ |
|---------|---------|-------|
| ![text2_Gx](./result/text2/text2_Gx.png) | ![text2_Gy](./result/text2/text2_Gy.png) | ![text2_G](./result/text2/text2_G.png) |

#### text3
| $G_x$ | $G_y$ | $G$ |
|---------|---------|-------|
| ![text3_Gx](./result/text3/text3_Gx.png) | ![text3_Gy](./result/text3/text3_Gy.png) | ![text3_G](./result/text3/text3_G.png) |

#### text4
| $G_x$ | $G_y$ | $G$ |
|---------|---------|-------|
| ![text4_Gx](./result/text4/text4_Gx.png) | ![text4_Gy](./result/text4/text4_Gy.png) | ![text4_G](./result/text4/text4_G.png) |

#### text5
| $G_x$ | $G_y$ | $G$ |
|---------|---------|-------|
| ![text5_Gx](./result/text5/text5_Gx.png) | ![text5_Gy](./result/text5/text5_Gy.png) | ![text5_G](./result/text5/text5_G.png) |

---

### 3. Бинаризация модуля градиента $G$ (различные пороги)

Для каждого изображения показаны результаты бинаризации при порогах 10, 20, 30, 40, 50, 60 и 70.

#### text1

| T=10 | T=20 |
|------|------|
| ![text1_binary_T10](./result/text1/text1_binary_T10.png) | ![text1_binary_T20](./result/text1/text1_binary_T20.png) |

| T=30 | T=40 |
|------|------|
| ![text1_binary_T30](./result/text1/text1_binary_T30.png) | ![text1_binary_T40](./result/text1/text1_binary_T40.png) |

| T=50 | T=60 |
|------|------|
| ![text1_binary_T50](./result/text1/text1_binary_T50.png) | ![text1_binary_T60](./result/text1/text1_binary_T60.png) |

| T=70 |
|------|
| ![text1_binary_T70](./result/text1/text1_binary_T70.png) |

Итог: для первого изображения оптимальным можно считать T=20, так как при меньших значениях высокий уровень шума, а при значениях выше пропадает четкоть букв.

#### text2

| T=10 | T=20 |
|------|------|
| ![text2_binary_T10](./result/text2/text2_binary_T10.png) | ![text2_binary_T20](./result/text2/text2_binary_T20.png) |

| T=30 | T=40 |
|------|------|
| ![text2_binary_T30](./result/text2/text2_binary_T30.png) | ![text2_binary_T40](./result/text2/text2_binary_T40.png) |

| T=50 | T=60 |
|------|------|
| ![text2_binary_T50](./result/text2/text2_binary_T50.png) | ![text2_binary_T60](./result/text2/text2_binary_T60.png) |

| T=70 |
|------|
| ![text2_binary_T70](./result/text2/text2_binary_T70.png) |

Итог: для второго изображения алгоритм показал себя ужасно при всех значениях T. Высокая зернистость мешает разобрать какие либо буквы до T=60 - после уже можно увидеть некоторые из них.

#### text3

| T=10 | T=20 |
|------|------|
| ![text3_binary_T10](./result/text3/text3_binary_T10.png) | ![text3_binary_T20](./result/text3/text3_binary_T20.png) |

| T=30 | T=40 |
|------|------|
| ![text3_binary_T30](./result/text3/text3_binary_T30.png) | ![text3_binary_T40](./result/text3/text3_binary_T40.png) |

| T=50 | T=60 |
|------|------|
| ![text3_binary_T50](./result/text3/text3_binary_T50.png) | ![text3_binary_T60](./result/text3/text3_binary_T60.png) |

| T=70 |
|------|
| ![text3_binary_T70](./result/text3/text3_binary_T70.png) |

Итог: для третьего изображения оператор Собеля показал аналогичную ситуацию с фото 2

#### text4

| T=10 | T=20 |
|------|------|
| ![text4_binary_T10](./result/text4/text4_binary_T10.png) | ![text4_binary_T20](./result/text4/text4_binary_T20.png) |

| T=30 | T=40 |
|------|------|
| ![text4_binary_T30](./result/text4/text4_binary_T30.png) | ![text4_binary_T40](./result/text4/text4_binary_T40.png) |

| T=50 | T=60 |
|------|------|
| ![text4_binary_T50](./result/text4/text4_binary_T50.png) | ![text4_binary_T60](./result/text4/text4_binary_T60.png) |

| T=70 |
|------|
| ![text4_binary_T70](./result/text4/text4_binary_T70.png) |

Итог: для четвертого изображения оптимальным порогом является T=70 где появляется баланс между сохранением полезных границ и подавлением лишнего шума.

#### text5

| T=10 | T=20 |
|------|------|
| ![text5_binary_T10](./result/text5/text5_binary_T10.png) | ![text5_binary_T20](./result/text5/text5_binary_T20.png) |

| T=30 | T=40 |
|------|------|
| ![text5_binary_T30](./result/text5/text5_binary_T30.png) | ![text5_binary_T40](./result/text5/text5_binary_T40.png) |

| T=50 | T=60 |
|------|------|
| ![text5_binary_T50](./result/text5/text5_binary_T50.png) | ![text5_binary_T60](./result/text5/text5_binary_T60.png) |

| T=70 |
|------|
| ![text5_binary_T70](./result/text5/text5_binary_T70.png) |

Итог: для пятого изображения приемлимый результат получается начиная с T=50 и улучшается по мере увеличения T.
