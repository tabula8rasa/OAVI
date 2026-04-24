# Лабораторная работа №3
## Фильтрация изображений и морфологические операции

**Вариант:** 4

---

Фильтрация полутоновых изображений медианным фильтром с окном 3×3.

$$\text{Mask} =
\begin{bmatrix}
1 & 1 & 1 \\
1 & 1 & 1 \\
1 & 1 & 1
\end{bmatrix}$$

### Используемые методы
- **Полутоновое преобразование**: взвешенное усреднение каналов RGB по формуле

$$
Y = 0.299 R + 0.587 G + 0.114 B
$$

- **Медианная фильтрация**: для каждого пикселя рассматривается окно 3×3. Значения яркости в окне сортируются, после чего центральному пикселю присваивается медианное значение. Для окна 3×3 медиана соответствует рангу 5/9.
- **Разностное изображение**: модуль разности между исходным полутоновым изображением и отфильтрованным изображением. Для улучшения видимости слабых изменений применяется умножение на 10 с ограничением значений до 255.

---

## 1. Исходные цветные и полутоновые изображения

| **text1** | **text1_gray** |
|:---:|:---:|
| ![text1](./result/text1_original.png) | ![text1_gray](./result/text1_gray.png) |

| **text2** | **text2_gray** |
|:---:|:---:|
| ![text2](./result/text2_original.png) | ![text2_gray](./result/text2_gray.png) |

| **text3** | **text3_gray** |
|:---:|:---:|
| ![text3](./result/text3_original.png) | ![text3_gray](./result/text3_gray.png) |

| **text4** | **text4_gray** |
|:---:|:---:|
| ![text4](./result/text4_original.png) | ![text4_gray](./result/text4_gray.png) |

| **text5** | **text5_gray** |
|:---:|:---:|
| ![text5](./result/text5_original.png) | ![text5_gray](./result/text5_gray.png) |

---

## 2. Полутоновые и отфильтрованные изображения
### Медианный фильтр, маска 3×3, ранг 5/9

| **text1_gray** | **text1_median_3x3** |
|:---:|:---:|
| ![text1_gray](./result/text1_gray.png) | ![text1_median_3x3](./result/text1_median_3x3.png) |

| **text2_gray** | **text2_median_3x3** |
|:---:|:---:|
| ![text2_gray](./result/text2_gray.png) | ![text2_median_3x3](./result/text2_median_3x3.png) |

| **text3_gray** | **text3_median_3x3** |
|:---:|:---:|
| ![text3_gray](./result/text3_gray.png) | ![text3_median_3x3](./result/text3_median_3x3.png) |

| **text4_gray** | **text4_median_3x3** |
|:---:|:---:|
| ![text4_gray](./result/text4_gray.png) | ![text4_median_3x3](./result/text4_median_3x3.png) |

| **text5_gray** | **text5_median_3x3** |
|:---:|:---:|
| ![text5_gray](./result/text5_gray.png) | ![text5_median_3x3](./result/text5_median_3x3.png) |

---

## 3. Разностные изображения и контрастированные версии

| **text1_diff** | **text1_diff_x10** |
|:---:|:---:|
| ![text1_diff](./result/text1_diff.png) | ![text1_diff_x10](./result/text1_diff_x10.png) |

| **text2_diff** | **text2_diff_x10** |
|:---:|:---:|
| ![text2_diff](./result/text2_diff.png) | ![text2_diff_x10](./result/text2_diff_x10.png) |

| **text3_diff** | **text3_diff_x10** |
|:---:|:---:|
| ![text3_diff](./result/text3_diff.png) | ![text3_diff_x10](./result/text3_diff_x10.png) |

| **text4_diff** | **text4_diff_x10** |
|:---:|:---:|
| ![text4_diff](./result/text4_diff.png) | ![text4_diff_x10](./result/text4_diff_x10.png) |

| **text5_diff** | **text5_diff_x10** |
|:---:|:---:|
| ![text5_diff](./result/text5_diff.png) | ![text5_diff_x10](./result/text5_diff_x10.png) |
