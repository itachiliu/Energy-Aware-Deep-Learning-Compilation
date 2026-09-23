# 编译决策空间扫描汇总（36 配置 × 8 稳态窗口）

> 能耗为 batch 调用口径；J/inf(net) 扣 idle；static% = idle/平均功耗。

| model | stack | prec | batch | opt | lat_ms | p95 | J/gross | J/net | EDP | static% |
|---|---|---|---|---|---|---|---|---|---|---|
| mobilenetv2 | ort-cuda | fp32 | 1 | all | 1.7369 | 1.7598 | 0.141686 | 0.07632 | 0.000246097 | 46.1 |
| mobilenetv2 | ort-cuda | fp32 | 1 | basic | 1.7302 | 1.7673 | 0.141099 | 0.076411 | 0.000244133 | 45.8 |
| mobilenetv2 | ort-cuda | fp32 | 1 | disable | 1.7374 | 1.7502 | 0.141393 | 0.076848 | 0.000245654 | 45.6 |
| mobilenetv2 | ort-cuda | fp32 | 1 | extended | 1.7103 | 1.7344 | 0.139711 | 0.075517 | 0.000238952 | 45.9 |
| mobilenetv2 | ort-cuda | fp32 | 16 | all | 3.8535 | 3.9501 | 0.694139 | 0.549734 | 0.002674898 | 20.8 |
| mobilenetv2 | ort-cuda | fp32 | 16 | basic | 3.8457 | 3.8241 | 0.695462 | 0.552943 | 0.002674561 | 20.5 |
| mobilenetv2 | ort-cuda | fp32 | 16 | disable | 3.8861 | 3.9243 | 0.704976 | 0.560808 | 0.002739627 | 20.5 |
| mobilenetv2 | ort-cuda | fp32 | 16 | extended | 3.8063 | 3.862 | 0.683959 | 0.541531 | 0.002603355 | 20.8 |
| mobilenetv2 | torch-eager | fp32 | 1 | - | 6.4698 | 7.0708 | 0.257526 | 0.014829 | 0.001666811 | 94.2 |
| mobilenetv2 | torch-eager | fp16 | 1 | - | 7.3414 | 7.525 | 0.287029 | 0.012366 | 0.002107222 | 95.7 |
| mobilenetv2 | torch-eager | fp32 | 16 | - | 6.3376 | 6.4705 | 0.71888 | 0.482494 | 0.004556011 | 32.9 |
| mobilenetv2 | torch-eager | fp16 | 16 | - | 7.4961 | 7.804 | 0.457837 | 0.178398 | 0.003431911 | 61 |
| resnet50 | ort-cuda | fp32 | 1 | all | 3.5972 | 3.7434 | 0.397801 | 0.262436 | 0.001431017 | 34 |
| resnet50 | ort-cuda | fp32 | 1 | basic | 3.4308 | 3.5597 | 0.356954 | 0.227844 | 0.001224663 | 36.2 |
| resnet50 | ort-cuda | fp32 | 1 | disable | 3.5139 | 3.6486 | 0.36019 | 0.22793 | 0.00126576 | 36.7 |
| resnet50 | ort-cuda | fp32 | 1 | extended | 3.6091 | 3.6537 | 0.398325 | 0.262461 | 0.001437596 | 34.1 |
| resnet50 | ort-cuda | fp32 | 16 | all | 7.1919 | 7.3878 | 1.409566 | 1.140438 | 0.010137472 | 19.1 |
| resnet50 | ort-cuda | fp32 | 16 | basic | 7.2156 | 7.4426 | 1.420212 | 1.150365 | 0.010247622 | 19 |
| resnet50 | ort-cuda | fp32 | 16 | disable | 7.2976 | 7.679 | 1.445067 | 1.171902 | 0.010545718 | 18.9 |
| resnet50 | ort-cuda | fp32 | 16 | extended | 7.1454 | 7.2855 | 1.40868 | 1.141258 | 0.010065522 | 19 |
| resnet50 | torch-eager | fp16 | 1 | - | 8.3105 | 10.9058 | 0.353327 | 0.042621 | 0.002936344 | 87.9 |
| resnet50 | torch-eager | fp32 | 1 | - | 7.3341 | 7.4416 | 0.338223 | 0.064463 | 0.002480593 | 80.9 |
| resnet50 | torch-eager | fp16 | 16 | - | 8.1262 | 10.6648 | 1.070499 | 0.767716 | 0.00869939 | 28.3 |
| resnet50 | torch-eager | fp32 | 16 | - | 7.485 | 7.9225 | 1.349054 | 1.070896 | 0.010097794 | 20.6 |
| vit_b_16 | ort-cuda | fp32 | 1 | all | 2.857 | 2.854 | 0.480161 | 0.358 | 0.001371839 | 25.4 |
| vit_b_16 | ort-cuda | fp32 | 1 | basic | 3.2069 | 3.197 | 0.527014 | 0.390051 | 0.001690075 | 26 |
| vit_b_16 | ort-cuda | fp32 | 1 | disable | 3.2433 | 3.2331 | 0.528689 | 0.390555 | 0.001714671 | 26.1 |
| vit_b_16 | ort-cuda | fp32 | 1 | extended | 2.8452 | 2.844 | 0.479194 | 0.357524 | 0.001363394 | 25.4 |
| vit_b_16 | ort-cuda | fp32 | 16 | all | 14.6048 | 14.9051 | 3.619849 | 2.997 | 0.052867105 | 17.2 |
| vit_b_16 | ort-cuda | fp32 | 16 | basic | 18.8669 | 19.0506 | 4.690381 | 3.882234 | 0.088493118 | 17.2 |
| vit_b_16 | ort-cuda | fp32 | 16 | disable | 18.881 | 19.1539 | 4.687649 | 3.885637 | 0.088507998 | 17.1 |
| vit_b_16 | ort-cuda | fp32 | 16 | extended | 14.5786 | 14.7897 | 3.608707 | 2.996275 | 0.052609865 | 17 |
| vit_b_16 | torch-eager | fp16 | 1 | - | 5.8217 | 5.9701 | 0.296325 | 0.080496 | 0.001725292 | 72.8 |
| vit_b_16 | torch-eager | fp32 | 1 | - | 5.6961 | 5.7992 | 1.051112 | 0.838928 | 0.005987142 | 20.2 |
| vit_b_16 | torch-eager | fp16 | 16 | - | 6.4336 | 7.092 | 1.56691 | 1.329034 | 0.01008667 | 15.2 |
| vit_b_16 | torch-eager | fp32 | 16 | - | 40.6358 | 40.9814 | 10.117337 | 8.594468 | 0.411126702 | 15 |

## H2（每模型×batch：延迟最优 vs 能耗最优 gross vs EDP 最优）

- mobilenetv2 b1: 延迟最优=ort-cuda/fp32/opt2/b1 1.7103 ms | 能耗最优=ort-cuda/fp32/opt2/b1 0.139711 J | EDP最优=ort-cuda/fp32/opt2/b1 | divergent=no
- mobilenetv2 b16: 延迟最优=ort-cuda/fp32/opt2/b16 3.8063 ms | 能耗最优=torch-eager/fp16/eager/b16 0.457837 J | EDP最优=ort-cuda/fp32/opt2/b16 | divergent=YES
- resnet50 b1: 延迟最优=ort-cuda/fp32/opt1/b1 3.4308 ms | 能耗最优=torch-eager/fp32/eager/b1 0.338223 J | EDP最优=ort-cuda/fp32/opt1/b1 | divergent=YES
- resnet50 b16: 延迟最优=ort-cuda/fp32/opt2/b16 7.1454 ms | 能耗最优=torch-eager/fp16/eager/b16 1.070499 J | EDP最优=torch-eager/fp16/eager/b16 | divergent=YES
- vit_b_16 b1: 延迟最优=ort-cuda/fp32/opt2/b1 2.8452 ms | 能耗最优=torch-eager/fp16/eager/b1 0.296325 J | EDP最优=ort-cuda/fp32/opt2/b1 | divergent=YES
- vit_b_16 b16: 延迟最优=torch-eager/fp16/eager/b16 6.4336 ms | 能耗最优=torch-eager/fp16/eager/b16 1.56691 J | EDP最优=torch-eager/fp16/eager/b16 | divergent=no

分歧配置数：4/6

## ORT 图优化等级跨档极差（同模型×batch，J/inf gross）

- mobilenetv2 b1: 0.139711–0.141686 J（极差 1.4%）
- mobilenetv2 b16: 0.683959–0.704976 J（极差 3.1%）
- resnet50 b1: 0.356954–0.398325 J（极差 11.6%）
- resnet50 b16: 1.408680–1.445067 J（极差 2.6%）
- vit_b_16 b1: 0.479194–0.528689 J（极差 10.3%）
- vit_b_16 b16: 3.608707–4.690381 J（极差 30.0%）

> 36 配置全部成功；环境：A100-PCIe-40GB，driver 535.104.12，8×20s，cp310cu122。
