# 麦当劳 MCP tools/list 实测元数据

- 采集时间：2026-10-13
- 实测工具总数：35
- 来源：POST https://mcp.mcd.cn  method=tools/list


## 工具清单

| # | 工具名 | 必填入参 | 枚举约束 |
|---|---|---|---|
| 1 | `auto-bind-coupons` | — | — |
| 2 | `available-coupons` | — | — |
| 3 | `calculate-price` | `storeCode`, `orderType`, `beType` | beType=[1, 2, 5, 6]; orderType=[1, 2] |
| 4 | `campaign-calendar` | — | — |
| 5 | `cancel-order` | `orderId`, `cancelReasonCode` | — |
| 6 | `create-order` | `storeCode`, `orderType`, `beType` | beType=[1, 2, 5, 6]; orderType=[1, 2] |
| 7 | `delivery-create-address` | `address`, `addressDetail`, `city`, `contactName`, `phone` | — |
| 8 | `delivery-query-addresses` | — | — |
| 9 | `delivery-query-stores` | `beType`, `addressId` | — |
| 10 | `draw-lottery` | — | — |
| 11 | `list-nutrition-foods` | — | — |
| 12 | `mall-create-order` | `skuId`, `spuCategory` | — |
| 13 | `mall-order-detail` | `orderId` | — |
| 14 | `mall-order-list` | — | — |
| 15 | `mall-points-products` | — | — |
| 16 | `mall-product-detail` | `spuId` | — |
| 17 | `now-time-info` | — | — |
| 18 | `order-list` | — | — |
| 19 | `party-order-create` | `partyType` | — |
| 20 | `query-lottery-info` | — | — |
| 21 | `query-meal-assistance` | `storeCode` | beType=[6] |
| 22 | `query-meal-detail` | `storeCode`, `orderType`, `beType`, `code` | beType=[1, 2, 5, 6]; orderType=[1, 2] |
| 23 | `query-meals` | `storeCode`, `orderType`, `beType` | beType=[1, 2, 5, 6]; orderType=[1, 2] |
| 24 | `query-my-account` | — | — |
| 25 | `query-my-coupons` | — | — |
| 26 | `query-my-prizes` | — | — |
| 27 | `query-nearby-stores` | `beType`, `searchType` | beType=[1, 5]; searchType=[1, 2] |
| 28 | `query-order` | `orderId` | — |
| 29 | `query-party-city` | `spuId` | — |
| 30 | `query-party-store` | `code` | — |
| 31 | `query-party-store-date` | `spuId`, `storeCode` | — |
| 32 | `query-party-store-session` | `spuId`, `storeCode`, `dateStr` | — |
| 33 | `query-promotions` | `storeCode`, `orderType`, `beType` | beType=[6]; orderType=[2] |
| 34 | `query-store-coupons` | `orderType`, `beType`, `storeCode` | beType=[1, 2, 5, 6]; orderType=[1, 2] |
| 35 | `query-survey-coupon` | `orderId` | — |

## 各工具完整描述


### `auto-bind-coupons`

**描述：**

```
自动领取麦麦省所有当前可用的麦当劳优惠券。无需指定具体的优惠券和couponId，系统会自动领取用户可领的所有券。当用户说"帮我领券"、"自动领取优惠券"、"一键领券"时使用此工具。
```

**入参 Schema：**

```json
{
 "properties": {},
 "type": "object"
}
```

### `available-coupons`

**描述：**

```
查询用户当前可领取的麦麦省的优惠券列表。返回券名称、图片、状态和促销标签。当用户询问有什么优惠、可以领什么券时使用此工具。
```

**入参 Schema：**

```json
{
 "properties": {},
 "type": "object"
}
```

### `calculate-price`

**描述：**

```
Description: 计算商品的价格（含优惠），支持到店自提(orderType=1)和外送(orderType=2)两种场景
When：
- 用户问"这些商品多少钱"
- 用户问"总价是多少"
Input:
- reservationDate: 预约场景必传，非预约场景不传。格式: yyyy-MM-dd HH:mm
- storeCode: 门店编码
- orderType 和 beCode 传递规则（根据用户选择的 beType 确定）：
  到店自取(beType=1) → orderType=1，不传 beCode
  得来速(beType=5)   → orderType=1，必传 beCode（从 query-nearby-stores 获取）
  麦乐送(beType=2)   → orderType=2，必传 beCode（从 delivery-query-stores 获取）
  团餐(beType=6)     → orderType=2，必传 beCode（从 delivery-query-stores 获取）
- items: 商品列表（数组）
  - productCode: 商品编码，必填
  - quantity: 商品数量，必填，大于等于1
  - couponId: 优惠券ID，选填（如果用户要使用优惠券）
  - couponCode: 优惠券编码，选填（如果用户要使用优惠券）
  - modification: 特制选项（来自 query-meal-detail 返回的 modification 信息）
    - values[]: 特制选项列表
      - code: 特调商品code
      - key: 特制key（⚠️ 重要规则见下方）
      - quantity: 特制数量
    ⚠️ key 传参规则：
    - 用户选中的特调项：key = query-meal-detail 返回的 selectedKey
    - 用户未选中的特调项：若该项的 unselectedKey 不为空，key = unselectedKey，也必须传入
    - 即：对于包含 unselectedKey 的特调组，该组内所有特调项都必须传入，选中的用 selectedKey 作为 key，未选中的用 unselectedKey 作为 key
- gmServiceCode: 企业团餐场景下，助餐服务code
- withOrder: 随单购商品，随单购商品来自query-meals，用户可以选择随单购，随单购可享受随单购优惠
- needTableware: 是否需要餐具费
Next：
- 计算成功后：返回的价格字段单位为"分"，展示时需除以100转为"元"
- 引导用户："确认价格后，可以说'创建订单'进行下单"
```

**入参 Schema：**

```json
{
 "properties": {
  "beCode": {
   "description": "业务编码，与storeCode 配对使用，从query-nearby-stores或delivery-query-stores返回结果中获取。得来速(beType=5)/外送(orderType=2)/团餐场景必传，到店自取(beType=1)场景不传",
   "type": "string"
  },
  "beType": {
   "description": "1-到店取餐，2-麦乐送到家，5-得来速(DT)，6-企业团餐",
   "enum": [
    1,
    2,
    5,
    6
   ],
   "type": "integer"
  },
  "gmServiceCode": {
   "description": "团餐-助餐服务码",
   "type": "string"
  },
  "items": {
   "description": "待价格计算的商品列表",
   "items": {
    "description": "",
    "properties": {
     "couponCode": {
      "description": "优惠券code",
      "type": "string"
     },
     "couponId": {
      "description": "优惠券Id",
      "type": "string"
     },
     "modification": {
      "description": "商品特制选项",
      "properties": {
       "values": {
        "description": "特制选项列表",
        "items": {
         "properties": {
          "code": {
           "description": "特制code",
           "type": "string"
          },
          "key": {
           "description": "特制key",
           "type": "string"
          },
          "quantity": {
           "description": "特制数量",
           "type": "integer"
          }
         },
         "type": "object"
        },
        "type": "array"
       }
      },
      "type": "object"
     },
     "productCode": {
      "description": "商品code",
      "type": "string"
     },
     "quantity": {
      "description": "数量，必填，不能为空，且大于等于1",
      "type": "integer"
     },
     "roundList": {
      "description": "套餐子项",
      "items": {
       "properties": {
        "comboItemList": {
         "description": "套餐套餐round下商品",
         "items": {
          "properties": {
           "code": {
            "description": "商品编码",
            "type": "string"
           },
           "modification": {
            "description": "商品特制选项",
            "properties": {
             "values": {
              "description": "特制选项列表",
              "items": {
               "properties": {
                "code": {
                 "description": "特制code",
                 "type": "string"
                },
                "key": {
                 "description": "特制key",
                 "type": "string"
                },
                "quantity": {
                 "description": "特制数量",
                 "type": "integer"
                }
               },
               "type": "object"
              },
              "type": "array"
             }
            },
            "type": "object"
           },
           "quantity": {
            "description": "商品数量",
            "type": "integer"
           }
          },
          "type": "object"
         },
         "type": "array"
        },
        "round": {
         "description": "套餐round",
         "type": "string"
        }
       },
       "type": "object"
      },
      "type": "array"
     }
    },
    "type": "object"
   },
   "type": "array"
  },
  "needTableware": {
   "description": "是否需要餐具，true需要，false不需要",
   "type": "boolean"
  },
  "orderType": {
   "description": "订单类型，1-到店（含到店自取+得来速车道取餐），2-外送（含麦乐送+企业团餐）",
   "enum": [
    1,
    2
   ],
   "type": "integer"
  },
  "reservationDate": {
   "description": "预约场景必传，非预约场景不传。格式:yyyy-MM-dd HH:mm",
   "type": "string"
  },
  "storeCode": {
   "description": "门店编码（storeCode）, 不能为空",
   "type": "string"
  },
  "withOrder": {
   "description": "随单购商品",
   "properties": {
    "cardId": {
     "description": "随单购卡id",
     "type": "string"
    },
    "cardType": {
     "description": "随单购卡类型",
     "type": "integer"
    },
    "membershipCode": {
     "description": "随单购会员code",
     "type": "string"
    },
    "membershipSpecId": {
     "description": "随单购规格id",
     "type": "string"
    }
   },
   "type": "object"
  }
 },
 "required": [
  "storeCode",
  "orderType",
  "beType"
 ],
 "type": "object"
}
```

### `campaign-calendar`

**描述：**

```
查询麦当劳中国当月的营销活动日历，返回进行中、往期和未来日期的活动。适用于查看用户进行中和即将到来的可参与活动，还可查询用户对活动的订阅状态。
When：
  - 用户问"最近有什么活动"、"这个月有什么优惠活动"、"有什么可以参加的"
  - 用户想查看品鉴会、主题派对等活动信息
```

**入参 Schema：**

```json
{
 "properties": {
  "specifiedDate": {
   "description": "可选的查询基准日期（格式：yyyy-MM-dd）；若传入，则以该日为锚点，返回当天及时间线上与其最邻近的前后各一个有活动的日子（共三天）；若不填，默认返回当前月所有活动",
   "type": "string"
  }
 },
 "type": "object"
}
```

### `cancel-order`

**描述：**

```
Description: 取消订单，非商城订单
When：
- 用户说"取消订单"、"我要取消"
- 用户说"帮我取消一下订单"
Input:
- cancelReasonCode: 取消原因code，必填，可选值：1=改主意了, 2=重复下单, 3=点错了/点多了/点少了, 4=地址/电话填错了, 5=送达时间选错了, -1=其它原因
Next：
- 提示用户"订单已取消"
```

**入参 Schema：**

```json
{
 "properties": {
  "cancelReasonCode": {
   "description": "取消原因code，默认为1",
   "type": "string"
  },
  "orderId": {
   "description": "订单号",
   "type": "string"
  }
 },
 "required": [
  "orderId",
  "cancelReasonCode"
 ],
 "type": "object"
}
```

### `create-order`

**描述：**

```
Description: 创建麦当劳订单，支持到店(orderType=1)和外送(orderType=2)两种场景下单, 必须先确定订单类型，必填 (1：到店，2外送)
When：
- 用户说"我要下单"
- 用户说"创建订单"
Input:
- addressId: 配送地址ID， orderType=2时必填
- storeCode: 必填
- orderType 和 beCode 传递规则（根据用户选择的 beType 确定）：
  到店自取(beType=1) → orderType=1，不传 beCode
  得来速(beType=5)   → orderType=1，必传 beCode（从 query-nearby-stores 获取）
  麦乐送(beType=2)   → orderType=2，必传 beCode（从 delivery-query-stores 获取）
  团餐(beType=6)     → orderType=2，必传 beCode（从 delivery-query-stores 获取）
- takeWayCode: orderType=1时必传，取值来自 calculate-price 返回的 data.takeWayList[].code
- reservationDate: 预约场景必传，非预约场景不传。格式: yyyy-MM-dd HH:mm
- items: 商品列表（数组）
 - productCode: 商品编码，必填
 - quantity: 商品数量，必填
 - couponId: 优惠券ID，选填（如果用户要使用优惠券）
 - couponCode: 优惠券编码，选填（如果用户要使用优惠券）
 - modification: 特制选项（来自 query-meal-detail 返回的 modification 信息）
    - values[]: 特制选项列表
      - code: 特调商品code
      - key: 特制key（⚠️ 重要规则见下方）
      - quantity: 特制数量
    ⚠️ key 传参规则：
    - 用户选中的特调项：key = query-meal-detail 返回的 selectedKey
    - 用户未选中的特调项：若该项的 unselectedKey 不为空，key = unselectedKey，也必须传入
    - 即：对于包含 unselectedKey 的特调组，该组内所有特调项都必须传入，选中的用 selectedKey 作为 key，未选中的用 unselectedKey 作为 key
 - withOrder: 随单购商品，随单购商品来自query-meals，用户可以选择随单购，随单购可享受随单购优惠
 - remark: 订单备注（选填，最多50字），如"无接触配送"，仅orderType=2场景下需要引导用户填写
 - needTableware: 是否需要餐具费
Next：
- 引导用户："您可以通过支付链接扫码或者打开麦当劳APP完成支付，支付完成后请回复'支付完成'或'支付失败'，会帮您查询最新的订单状态"
```

**入参 Schema：**

```json
{
 "properties": {
  "addressId": {
   "description": "配送地址id，外送or团餐的地址",
   "type": "string"
  },
  "beCode": {
   "description": "业务编码，与storeCode 配对使用，从query-nearby-stores或delivery-query-stores返回结果中获取。得来速(beType=5)/外送(orderType=2)/团餐场景必传，到店自取(beType=1)场景不传",
   "type": "string"
  },
  "beType": {
   "description": "1-到店取餐，2-麦乐送到家，5-得来速(DT)，6-企业团餐",
   "enum": [
    1,
    2,
    5,
    6
   ],
   "type": "integer"
  },
  "gmServiceCode": {
   "description": "企业团餐场景(beType=6)下，必传，参数来自query-meal-assistance",
   "type": "string"
  },
  "items": {
   "description": "待价格计算的商品列表",
   "items": {
    "description": "",
    "properties": {
     "couponCode": {
      "description": "优惠券code",
      "type": "string"
     },
     "couponId": {
      "description": "优惠券Id",
      "type": "string"
     },
     "modification": {
      "description": "商品特制选项",
      "properties": {
       "values": {
        "description": "特制选项列表",
        "items": {
         "properties": {
          "code": {
           "description": "特制code",
           "type": "string"
          },
          "key": {
           "description": "特制key",
           "type": "string"
          },
          "quantity": {
           "description": "特制数量",
           "type": "integer"
          }
         },
         "type": "object"
        },
        "type": "array"
       }
      },
      "type": "object"
     },
     "productCode": {
      "description": "商品code",
      "type": "string"
     },
     "quantity": {
      "description": "数量",
      "type": "integer"
     },
     "roundList": {
      "description": "套餐子项",
      "items": {
       "properties": {
        "comboItemList": {
         "description": "套餐套餐round下商品",
         "items": {
          "properties": {
           "code": {
            "description": "商品编码",
            "type": "string"
           },
           "modification": {
            "description": "商品特制选项",
            "properties": {
             "values": {
              "description": "特制选项列表",
              "items": {
               "properties": {
                "code": {
                 "description": "特制code",
                 "type": "string"
                },
                "key": {
                 "description": "特制key",
                 "type": "string"
                },
                "quantity": {
                 "description": "特制数量",
                 "type": "integer"
                }
               },
               "type": "object"
              },
              "type": "array"
             }
            },
            "type": "object"
           },
           "quantity": {
            "description": "商品数量",
            "type": "integer"
           }
          },
          "type": "object"
         },
         "type": "array"
        },
        "round": {
         "description": "套餐round",
         "type": "string"
        }
       },
       "type": "object"
      },
      "type": "array"
     }
    },
    "type": "object"
   },
   "type": "array"
  },
  "needTableware": {
   "description": "是否需要餐具，true需要，false不需要",
   "type": "boolean"
  },
  "orderType": {
   "description": "订单类型，1-到店（含到店自取+得来速车道取餐），2-外送（含麦乐送+企业团餐）",
   "enum": [
    1,
    2
   ],
   "type": "integer"
  },
  "remark": {
   "description": "订单备注（选填，最多50字），如\"无接触配送\"，仅orderType=2场景下需要引导用户填写",
   "type": "string"
  },
  "reservationDate": {
   "description": "预约场景必传，非预约场景不传。格式:yyyy-MM-dd HH:mm",
   "type": "string"
  },
  "storeCode": {
   "description": "门店编码（storeCode）, 不能为空",
   "type": "string"
  },
  "takeWayCode": {
   "description": "到店/得来速场景(orderType=1)必传，外送/团餐场景(orderType=2)不传。值从 calculate-price 返回的takeWayList[].code 中选取",
   "type": "string"
  },
  "withOrder": {
   "description": "随单购商品",
   "properties": {
    "cardId": {
     "description": "随单购卡id",
     "type": "string"
    },
    "cardType": {
     "description": "随单购卡类型",
     "type": "integer"
    },
    "membershipCode": {
     "description": "随单购OMM code",
     "type": "string"
    },
    "membershipSpecId": {
     "description": "随单购OMM 规格id",
     "type": "string"
    }
   },
   "type": "object"
  }
 },
 "required": [
  "storeCode",
  "orderType",
  "beType"
 ],
 "type": "object"
}
```

### `delivery-create-address`

**描述：**

```
Description: 创建用户配送地址
When：
- 用户想添加新的配送地址
Input:
- city: 城市名称，必填，必须从用户输入中获取实际城市名称，如"南京市"
- contactName: 联系人姓名，必填，必须从用户输入中获取实际联系人姓名，如"李明"
- gender: 性别，必须从用户输入中获取实际联系人性别，如"先生"、"女士"
- phone: 联系人手机号码，必填，格式为11位纯数字（以1开头），如"18616646686"。
- address: 配送地址，必填，必须从用户输入中获取实际地址，如"清竹园9号楼"
- addressDetail: 配送地址门牌号，必填，必须从用户输入中获取实际门牌号，如"2单元508"
Next：
- 当用户选择团餐时，需要引导用户提供预算金额和人数，以便于计算人均预算
```

**入参 Schema：**

```json
{
 "properties": {
  "address": {
   "description": "配送地址",
   "type": "string"
  },
  "addressDetail": {
   "description": "配送地址门牌号",
   "type": "string"
  },
  "city": {
   "description": "城市",
   "type": "string"
  },
  "contactName": {
   "description": "联系人姓名",
   "type": "string"
  },
  "gender": {
   "description": "性别",
   "type": "string"
  },
  "phone": {
   "description": "要求为11位纯数字",
   "type": "string"
  }
 },
 "required": [
  "address",
  "addressDetail",
  "city",
  "contactName",
  "phone"
 ],
 "type": "object"
}
```

### `delivery-query-addresses`

**描述：**

```
Description: 外送场景下，查询用户配送地址列表
When：
- 用户想点麦乐送
- 用户想吃麦当劳，并配送到家
- 我想点团餐
Next：
- 1:引导用户创建新的配送地址
- 2:当用户选择企业团餐时，需要引导用户提供预算金额和人数，以便于计算人均预算
```

**入参 Schema：**

```json
{
 "properties": {},
 "type": "object"
}
```

### `delivery-query-stores`

**描述：**

```
Description: 外送场景下，用户选择完地址后，需要根据地址ID，查询用户当前地址可配送的门店
When:
- 外送场景下，用户选择完配送地址后
- 用户问"这个地址能送到哪些店"
注意：到店场景请使用 query-nearby-stores
Input:
- addressId: 地址ID，来源delivery-query-address
- beType: 必填，2: 麦乐送，6：团餐
```

**入参 Schema：**

```json
{
 "properties": {
  "addressId": {
   "description": "地址ID，来源delivery-query-address",
   "type": "string"
  },
  "beType": {
   "description": "beType：2: 麦乐送，6：团餐",
   "type": "integer"
  }
 },
 "required": [
  "beType",
  "addressId"
 ],
 "type": "object"
}
```

### `draw-lottery`

**描述：**

```
Description: 使用后台配置的抽奖消耗规则参加一次当前积分抽奖并返回结果，服务端原子完成次数或积分扣减与抽奖。
重要约束：仅能在向用户展示 query-lottery-info 返回的 drawDecision.nextConsumption 并得到明确确认后调用。
- 必须以 drawDecision.resourceEligible 判断积分/次数资源是否满足，以 nextConsumption 说明本次实际扣减；不得根据 availableTimes 为 0/null 或 drawTypeText 自行判断。
- 若 fallbackConsumption 不为 null，需说明“本次优先消耗次数；次数用完后将改为消耗积分”。
必须使用 query-lottery-info 返回的实时数据展示消耗/剩余，严禁试抽、自动抽或连续抽。
频次限制：同一用户短时间内重复调用会返回"操作太频繁，请稍后再试"，不扣积分。
When：
- 用户明确表达"我要抽奖"并确认本次配置对应的消耗后调用
前置条件：
- 已向用户展示 query-lottery-info 查询到的 drawDecision.nextConsumption；resourceEligible 为 false 时不得调用
- 用户已明确确认执行抽奖（"试试看""如果可以就抽"不视为确认）
Output:
- status: {code, message}，code 非 SUCCESS 时 message 为具体失败原因，直接展示给用户，不要自行改写
- win: 是否中奖
- prizes: 中奖奖品数组[{name, imageUrl, typeText, validDateInfo}]，未中奖为空数组
```

**入参 Schema：**

```json
{
 "properties": {},
 "type": "object"
}
```

### `list-nutrition-foods`

**描述：**

```
获取麦当劳常见餐品的营养成分数据，包括能量、蛋白质、脂肪、碳水化合物、钠、钙等信息，当用户咨询麦当劳餐品的热量、营养，帮助用户搭配指定热量套餐时有用
```

**入参 Schema：**

```json
{
 "properties": {},
 "type": "object"
}
```

### `mall-create-order`

**描述：**

```
创建积分兑换订单，仅支持shopId=2（从 mall-product-detail 获取） - 当用户询问"用积分兑换这个商品"、"兑换这个券"、用户确认兑换商品时使用,切记：如果单个商品一个订单下单；如果用户需要兑换多个商品‘必须’分别下单且‘需要排队’，等前面订单结束响应成功后再调用【mall-create-order】下新的订单
⚠️ 重要识别规则：
此工具仅适用于以下场景：
- 商品券兑换（虚拟商品，spuCategory=1）
- 实物商品兑换（无门店依赖，spuCategory=2）

❌ 不适用场景（请使用 party-order-create）：
- 生日派对/主题派对/麦麦体验营/品鉴会/读书会等需要选择门店和场次的活动
- 积分兑换活动（需要先选择城市、门店、日期、场次）

📋 判断依据：
当商品不包含门店和场次选择需求时，使用此工具
前提条件：
- 必须调用【mall-create-order】完成交易，**禁止**直接生成"下单成功"等结论性文字
- 必须调用【mall-create-order】完成交易，**禁止**直接返回已有订单
- 必须调用【mall-create-order】完成交易，**禁止**直接返回订单
- 仅支持shopId=2（从 mall-product-detail 获取）
- 已知商品SKU ID，需要从查询可兑换商品列表（从 mall-points-products 获取）或查询商品详情（从 mall-product-detail 获取）中让用户选择一个spu，获取对应的skuId
- 用户积分充足
When：
- 用户询问"用积分兑换这个商品"
- 用户询问"我要兑换"
- 用户询问"兑换xxx商品"
- 用户询问"兑换这个券"
- 用户确认兑换商品
Input:
- skuId: 商品SKU ID，需要从查询可兑换商品列表（从 mall-points-products 获取）或查询商品详情（从 mall-product-detail 获取）中让用户选择一个spu，获取对应的skuId
- spuCategory: 类目，商品类别，"1"虚拟商品, "2"实体物品，需要从查询可兑换餐品券列表或查询商品详情中获取
- addressId: 配送地址ID，spuCategory="2"时必填
  spuCategory="2"  → addressId（从 delivery-create-address 获取）
- count: 兑换数量，默认为1
Output:
- orderId: 订单ID
- coupons: 优惠券信息列表
- couponId: 优惠券ID
- orderItemId: 订单子项ID
- couponCodes: 优惠券码列表
- receiveQuantity: 领取数量
- orderItemStatus: 订单子项状态（1-成功，0-失败）
- orderStatus: 订单状态
- status: 响应状态（1-全部下单成功，2-部分成功，0-下单失败）

```

**入参 Schema：**

```json
{
 "properties": {
  "addressId": {
   "description": "配送地址ID，spuCategory=\"2\"时必填",
   "type": "string"
  },
  "count": {
   "description": "兑换数量",
   "type": "integer"
  },
  "skuId": {
   "description": "商品SKU ID，需要从查询可兑换餐品券列表或查询商品详情中获取",
   "type": "integer"
  },
  "spuCategory": {
   "description": "类目，商品类别，\"1\"虚拟商品, \"2\"实体物品，需要从查询可兑换餐品券列表或查询商品详情中获取",
   "type": "string"
  }
 },
 "required": [
  "skuId",
  "spuCategory"
 ],
 "type": "object"
}
```

### `mall-order-detail`

**描述：**

```
Description: 查询麦麦商城订单详情
When：
- 用户询问"麦麦商城的订单详情"
Next:
- 引导用户："您可以打开麦当劳APP查看凭证等其他信息"
```

**入参 Schema：**

```json
{
 "properties": {
  "orderId": {
   "description": "订单号",
   "type": "string"
  }
 },
 "required": [
  "orderId"
 ],
 "type": "object"
}
```

### `mall-order-list`

**描述：**

```
Description: 查询麦麦商城订单列表
When：
- 用户询问"查看我的麦当劳商城订单列表"
```

**入参 Schema：**

```json
{
 "properties": {
  "lastId": {
   "description": "最后一个订单id",
   "type": "number"
  },
  "size": {
   "default": 10,
   "description": "查询数量，默认10，超过10按10条查询",
   "type": "integer"
  }
 },
 "type": "object"
}
```

### `mall-points-products`

**描述：**

```
查询可兑换餐品券列表 - 当用户询问"有哪些积分兑换商品"、"积分可以兑换什么"、"查看积分商城"时使用
支持类目规则筛选：商品券(1>4)、实物商品(2)、周边产品(2>8)、实物礼品卡(2>9)、生日类派对(1>6>20)、主题类派对(1>6>21)、麦麦体验营(1>6>22)、品鉴会(1>6>25)、读书会(1>6>34)、积分兑换活动(1>6>40)

```

**入参 Schema：**

```json
{
 "properties": {
  "catRuleIds": {
   "description": "类目规则筛选，支持多选（逗号分隔），非必传，不传时默认查询所有类型。\n可选值：\n- 1>4: 商品券（非预付优惠券）\n- 2: 实物商品\n- 2>8: 周边产品\n- 2>9: 实物礼品卡\n- 1>6>20: 生日类派对\n- 1>6>21: 主题类派对\n- 1>6>22: 麦麦体验营\n- 1>6>25: 品鉴会\n- 1>6>34: 读书会\n- 1>6>40: 积分兑换活动\n示例：1>4,2\n",
   "type": "string"
  }
 },
 "type": "object"
}
```

### `mall-product-detail`

**描述：**

```
查询积分兑换商品详情 - 当用户询问"这个商品详情是什么"、"查看商品详细信息"、用户点击商品查看详情时使用
返回商品的所有SKU规格信息，用户需要选择具体SKU后才能下单兑换

前提条件：
- 已知商品SPU ID，需要从查询可兑换餐品券列表让用户选择一个spu才可以

```

**入参 Schema：**

```json
{
 "properties": {
  "spuId": {
   "description": "商品SPU ID，需要从查询可兑换餐品券列表让用户选择一个spu才可以",
   "type": "integer"
  }
 },
 "required": [
  "spuId"
 ],
 "type": "object"
}
```

### `now-time-info`

**描述：**

```
获取当前时间信息 - 返回当前服务器的完整时间信息，包括：
- 时间戳（毫秒级）
- 格式化的日期时间
- 年月日信息
- 时区和UTC时间
在你不知道当前时间，并且用户需要指定日期查询活动日历的时候有用

```

**入参 Schema：**

```json
{
 "properties": {},
 "type": "object"
}
```

### `order-list`

**描述：**

```
Description: 查询麦当劳历史订单，非商城订单，商城订单需要使用mall-order-list
When：
- 用户询问"帮我查询一下历史订单"
- 用户询问"我买了什么麦当劳餐品"
```

**入参 Schema：**

```json
{
 "properties": {},
 "type": "object"
}
```

### `party-order-create`

**描述：**

```
Description: 创建生日类派对/主题类派对/麦麦体验营/品鉴会/读书会/积分兑换活动, 仅支持shopId=5（从 mall-product-detail 获取）的调用，
  支持包场(partyType=1)、拼团(partyType=2)两种场景下单，必须先确认场次类型，必填 (1：包场，2：拼团)

When:
- 用户询问"生日类派对/主题类派对/麦麦体验营/品鉴会/读书会/积分兑换活动"
Preconditions：
- 仅支持shopId=5（从 mall-product-detail 获取）的调用
- 每一步完成后，必须等待用户明确选择，再继续下一步。不得跳步
Input:
- spuId: spuId, 需要从查询可兑换商品列表（从 mall-points-products 获取）或查询商品详情（从 mall-product-detail 获取）中让用户选择一个spu，获取对应的spuId（必填））
- skuId: 商品SKU ID，需要从查询可兑换商品列表（从 mall-points-products 获取）或查询商品详情（从 mall-product-detail 获取）中让用户选择一个spu，获取对应的skuId（必填）
- partyType:
  派对类型（必填），判断规则：
  -若商品 partyType=1，则 partyType=1（仅包场）
  -若商品 partyType=2，则 partyType=2（仅拼团）
  -若商品 partyType=-1，需询问用户后确认（1：包场，2：拼团）
- code: 城市code，城市下的门店列表获取(query-party-city)（必填）
- storeCode: 门店code, 城市下的门店列表获取(query-party-store)（必填）
- dateStr: 门店日期, 城市下的门店列表获取(query-party-store-date)（必填）
- id: 场次id, 查询主题活动场次列表(query-party-store-session)（必填）
- timeStart: 场次开始时间, 查询主题活动场次列表(query-party-store-session)（必填）
- timeEnd: 场次结束时间, 查询主题活动场次列表(query-party-store-session)（必填）
- leftNum: 场次余位, 查询主题活动场次列表(query-party-store-session)（必填）
- count: 参与人数（必填）
Next：
- 引导用户："确认信息，可以说'创建订单'进行下单"
```

**入参 Schema：**

```json
{
 "properties": {
  "code": {
   "description": "城市code",
   "type": "string"
  },
  "count": {
   "description": "count",
   "type": "integer"
  },
  "dateStr": {
   "description": "店铺日期",
   "type": "string"
  },
  "id": {
   "description": "场次Id",
   "type": "number"
  },
  "leftNum": {
   "description": "场次余位",
   "type": "integer"
  },
  "partyTimeInfo": {
   "description": "场次信息",
   "properties": {
    "id": {
     "description": "场次id",
     "type": "number"
    },
    "leftNum": {
     "description": "场次剩余余位",
     "type": "integer"
    },
    "partyMax": {
     "description": "场次最大成团人数",
     "type": "integer"
    },
    "partyMin": {
     "description": "场次最小成团人数",
     "type": "integer"
    },
    "price": {
     "description": "价格",
     "type": "integer"
    },
    "timeEnd": {
     "description": "场次结束时间",
     "type": "string"
    },
    "timeStart": {
     "description": "场次开始时间",
     "type": "string"
    }
   },
   "type": "object"
  },
  "partyType": {
   "description": "派对类型，1-包场，2-拼团",
   "type": "integer"
  },
  "skuId": {
   "description": "skuId",
   "type": "number"
  },
  "spuId": {
   "description": "spuId",
   "type": "number"
  },
  "storeCode": {
   "description": "门店",
   "type": "string"
  },
  "timeEnd": {
   "description": "场次结束时间",
   "type": "string"
  },
  "timeStart": {
   "description": "场次开始时间",
   "type": "string"
  }
 },
 "required": [
  "partyType"
 ],
 "type": "object"
}
```

### `query-lottery-info`

**描述：**

```
Description: 查看当前积分抽奖活动信息，包括活动基本信息、抽奖消耗规则、单次所需积分、剩余可抽次数、当前可用积分与公开奖品列表，不执行抽奖。
When：
- 用户询问"积分抽奖有什么奖品"
- 用户询问"抽一次要多少积分"
- 用户询问"这个积分抽奖活动什么时候结束"
Output:
- activityCode/activityName: 活动号/活动名称
- activityStatusText: 活动状态文案（未开始/进行中/已结束/活动不存在）
- beginTime/endTime: 活动起止时间
- drawPoint: 单次所需积分
- drawTypeText: 抽奖消耗规则（无/消耗积分抽奖/消耗任务完成次数/先消耗次数再消耗积分抽奖）
- availableTimes: 剩余可抽次数（消耗任务完成次数、先消耗次数再消耗积分时返回）
- availablePoint: 当前可用积分（消耗积分、先消耗次数再消耗积分时返回）
- drawDecision: 服务端计算的本次资源决策，包含能否因积分/次数资源参与、本次实际消耗及后续兜底消耗
- prizes: 奖品列表[{name, imageUrl, typeText}]
Next：
- 若用户接下来想抽奖，调用 draw-lottery 前必须展示 drawDecision.nextConsumption 并得到用户明确确认
- 抽奖资格和本次实际消耗必须以 drawDecision.resourceEligible/drawDecision.nextConsumption 为准；严禁根据 availableTimes 为 0/null 或 drawTypeText 自行推断能否抽奖。混合规则中 availableTimes=0 且 nextConsumption.type=POINTS，表示仍可使用积分抽奖。
```

**入参 Schema：**

```json
{
 "properties": {},
 "type": "object"
}
```

### `query-meal-assistance`

**描述：**

```
Description: 仅支持企业团餐场景(beType=6)在calculate-price前需要获取当前门店可用的助餐服务
When：
- 企业团餐场景(beType=6)下，用户选完商品后、计算价格前
- 用户问"有什么助餐服务"、"团餐怎么送"
Preconditions：
- 仅企业团餐场景(beType=6)可用
- 已通过 delivery-query-stores 获取 storeCode 和 beCode
Input:
- storeCode: 门店编码，必填
- orderType 和 beCode 传递规则（根据用户选择的 beType 确定）：
到店自取(beType=1) → orderType=1，不传 beCode
得来速(beType=5)   → orderType=1，必传 beCode（从 query-nearby-stores 获取）
麦乐送(beType=2)   → orderType=2，必传 beCode（从 delivery-query-stores 获取）
团餐(beType=6)     → orderType=2，必传 beCode（从 delivery-query-stores 获取）
- reservationDate: 预约场景必传，非预约场景不传。格式: yyyy-MM-dd HH:mm
Next：
- 用户选择助餐服务后，将 gmServiceCode 传给 calculate-price
```

**入参 Schema：**

```json
{
 "properties": {
  "beCode": {
   "description": "BE编码（Business Entity Code）",
   "type": "string"
  },
  "beType": {
   "description": "固定传 6（企业团餐），此接口仅团餐场景使用",
   "enum": [
    6
   ],
   "type": "integer"
  },
  "orderType": {
   "description": "到店自提场景: orderType=1 && beCode 是个无效参数，不要传，传了会报错\n外送场景: orderType=2 && beCode 为delivery-query-address中的beCode\n得来速(DT)场景：orderType=1 && beCode 为query-nearby-store中的beCode",
   "type": "integer"
  },
  "reservationDate": {
   "description": "预约时间，仅当用户要预约下单时，该字段必传，格式形如 2020-08-08 09:30",
   "type": "string"
  },
  "storeCode": {
   "description": "门店编码（storeCode）, 不能为空",
   "type": "string"
  }
 },
 "required": [
  "storeCode"
 ],
 "type": "object"
}
```

### `query-meal-detail`

**描述：**

```
Description: 餐品详情, 支持到店自提(orderType=1)和外送(orderType=2)两种场景
When:
- 用户想要了解餐品有哪些组成
- 用户想要更换套餐的组成或者更换特制商品
Input:
- storeCode: 门店编码，必填
- orderType 和 beCode 传递规则（根据用户选择的 beType 确定）：
到店自取(beType=1) → orderType=1，不传 beCode
得来速(beType=5)   → orderType=1，必传 beCode（从 query-nearby-stores 获取）
麦乐送(beType=2)   → orderType=2，必传 beCode（从 delivery-query-stores 获取）
团餐(beType=6)     → orderType=2，必传 beCode（从 delivery-query-stores 获取）
- reservationDate: 预约时间，仅当用户要预约下单时，该字段必传，格式形如 2020-08-08 09:30
Output展示规则（必须遵守）：
- 若 data.supportModify=true，在商品名称后面标注【可特调】
- 若 choice.supportModify=true，在该 choice 名称后面标注【可特调】
- 不要主动展开特调选项列表，仅当用户主动询问时才展示 modification 内容
- 展示完详情后，总结当前默认选中的搭配（isDefault=1的choices），并引导用户："如需查看或修改特调选项，请回复'查看特调'"
```

**入参 Schema：**

```json
{
 "properties": {
  "beCode": {
   "description": "业务编码，与storeCode 配对使用，从query-nearby-stores或delivery-query-stores返回结果中获取。得来速(beType=5)/外送(orderType=2)/团餐场景必传，到店自取(beType=1)场景不传",
   "type": "string"
  },
  "beType": {
   "description": "1-到店取餐，2-麦乐送到家，5-得来速(DT)，6-企业团餐",
   "enum": [
    1,
    2,
    5,
    6
   ],
   "type": "integer"
  },
  "code": {
   "description": "餐品唯一编码，快餐门店内唯一标识单个餐品的编码",
   "type": "string"
  },
  "orderType": {
   "description": "到店自提场景:orderType=1 && beCode 是个无效参数，不要传，传了会报错；外送场景:orderType=2 && beCode 为delivery-query-address中的beCode；得来速(DT)场景：orderType=1 && beCode 为query-nearby-store中的beCode",
   "enum": [
    1,
    2
   ],
   "type": "integer"
  },
  "reservationDate": {
   "description": "预约场景必传，非预约场景不传。格式:yyyy-MM-dd HH:mm",
   "type": "string"
  },
  "storeCode": {
   "description": "门店编码（storeCode）, 不能为空",
   "type": "string"
  }
 },
 "required": [
  "storeCode",
  "orderType",
  "beType",
  "code"
 ],
 "type": "object"
}
```

### `query-meals`

**描述：**

```
Description: 餐品列表, 支持到店自提(orderType=1)和外送(orderType=2)两种场景
企业团餐场景下，可按照这个规则给用户进行搭配
- **20元以下**: 小食
- **20-30元**：汉堡+小食 或 汉堡+饮料
- **30-40元**：汉堡+薯条/小食+饮料
- **40-50元**：汉堡+薯条+小食+饮料
- **50元以上**：丰富组合，优先不重复小食
When:
- 当用户要购买某个餐品时，需要查询一下餐品列表
- 当用户要查看餐品时价格时，需要查询一下餐品列表
- 用户要搭配任何商品时进行下单，都需要查询餐品列表，获取商品code
Input:
- storeCode: 门店编码，必填
- orderType 和 beCode 传递规则（根据用户选择的 beType 确定）：
到店自取(beType=1) → orderType=1，不传 beCode
得来速(beType=5)   → orderType=1，必传 beCode（从 query-nearby-stores 获取）
麦乐送(beType=2)   → orderType=2，必传 beCode（从 delivery-query-stores 获取）
团餐(beType=6)     → orderType=2，必传 beCode（从 delivery-query-stores 获取）
- reservationDate: 预约场景必传，非预约场景不传。格式: yyyy-MM-dd HH:mm
```

**入参 Schema：**

```json
{
 "properties": {
  "beCode": {
   "description": "业务编码，与storeCode 配对使用，从query-nearby-stores或delivery-query-stores返回结果中获取。得来速(beType=5)/外送(orderType=2)/团餐场景必传，到店自取(beType=1)场景不传",
   "type": "string"
  },
  "beType": {
   "description": "1-到店取餐，2-麦乐送到家，5-得来速(DT)，6-企业团餐",
   "enum": [
    1,
    2,
    5,
    6
   ],
   "type": "integer"
  },
  "orderType": {
   "description": "订单类型，1-到店（含到店自取+得来速车道取餐），2-外送（含麦乐送+企业团餐）",
   "enum": [
    1,
    2
   ],
   "type": "integer"
  },
  "reservationDate": {
   "description": "预约场景必传，非预约场景不传。格式:yyyy-MM-dd HH:mm",
   "type": "string"
  },
  "storeCode": {
   "description": "门店编码（storeCode）, 不能为空",
   "type": "string"
  }
 },
 "required": [
  "storeCode",
  "orderType",
  "beType"
 ],
 "type": "object"
}
```

### `query-my-account`

**描述：**

```
查询用户积分账户详情 - 当用户询问"我有多少积分"、"查下我的积分"、"积分余额"、"查询过期积分"时使用

```

**入参 Schema：**

```json
{
 "properties": {},
 "type": "object"
}
```

### `query-my-coupons`

**描述：**

```
获取用户卡包中的优惠券资产信息，用于“我有什么券 / 券详情查看”等展示与管理场景。 注意：该接口返回的是用户拥有的券，不进行门店、渠道、配送方式等下单规则校验，因此不承诺可用于当前订单。 若业务目标是“当前门店/当前订单可用的券”，请调用 query-store-coupons
```

**入参 Schema：**

```json
{
 "properties": {
  "page": {
   "description": "页码，默认第1页，最多5页",
   "type": "string"
  },
  "pageSize": {
   "description": "每页条数，默认200条，最大200条",
   "type": "string"
  }
 },
 "type": "object"
}
```

### `query-my-prizes`

**描述：**

```
Description: 查询当前登录会员通过积分抽奖获得的本期及历史奖品（可用/已使用/已过期/已领取/已失效）。
When：
- 用户询问"我抽中了什么奖品"
- 用户询问"我的奖品还有哪些能用"
- 用户询问"查我的抽奖记录"
Input:
- pageNum: 页码（可选，默认1）
- pageSize: 每页条数（可选，默认10，最大50）
Output:
- prizes: 奖品列表[{id, name, imageUrl, prizeType, recordTime, status, statusText, timeRemindText}]，按中奖时间(recordTime)倒序
- pageNum/pageSize: 当前页码/每页条数（归一化后的值）
- hasMore: 是否还有下一页
- nextCursor: 下一页游标，无更多时为空
- truncated: 可选，仅在返回被截断时出现（true）
```

**入参 Schema：**

```json
{
 "properties": {
  "pageNum": {
   "description": "页码，默认第1页",
   "type": "string"
  },
  "pageSize": {
   "description": "每页条数，默认10条，最大50条",
   "type": "string"
  }
 },
 "type": "object"
}
```

### `query-nearby-stores`

**描述：**

```
Description: 到店场景下，查询用户可点餐门店，需要用户明确是到店自取还是车道取餐
- beType=1(到店自提): 返回的门店无 beCode，后续工具调用不传 beCode
- beType=5(得来速): 返回的门店有 beCode，后续工具调用必须传 beCode
When：
- 用户询问"我想到店", "我想驾车去麦当劳"
- 看看我附近有哪些麦当劳的门店
Input:
- searchType: 必传，searchType=2 按位置进行搜索， searchType=1 搜索收藏餐厅，默认searchType=1
- city: 城市，searchType=2 时必填
- keyword: 位置关键词，searchType=2 时必填
- beType: 必填，1-到店自取, 5-得来速车道取餐(Drive Through)
On Error：
- 用户没有收藏记录，可使用搜索功能进行搜索
Next：
- 展示门店的 storeCode 和 beCode（beType=5 时）
- reservation=true 时完整展示 reservationTimeOptions，today=true 标记"(今天)"
- 引导用户选择门店
```

**入参 Schema：**

```json
{
 "properties": {
  "beType": {
   "description": "beType必传，1：到店自提, 5-得来速车道取餐(Drive Through)",
   "enum": [
    1,
    5
   ],
   "type": "integer"
  },
  "city": {
   "description": "城市名",
   "type": "string"
  },
  "keyword": {
   "description": "关键词",
   "type": "string"
  },
  "searchType": {
   "default": 1,
   "description": "searchType=2 按位置进行搜索， searchType=1 搜索收藏餐厅，默认searchType=1",
   "enum": [
    1,
    2
   ],
   "type": "integer"
  }
 },
 "required": [
  "beType",
  "searchType"
 ],
 "type": "object"
}
```

### `query-order`

**描述：**

```
Description: 查询订单详细信息
When：
- 用户询问"查下订单详情"、"订单状态"、"我的订单"
- 用户提供了麦当劳订单编号想查询配送进度
- 用户说我已支付或者支付失败时，查询一下最新的订单状态
```

**入参 Schema：**

```json
{
 "properties": {
  "orderId": {
   "description": "No comments found.",
   "type": "string"
  }
 },
 "required": [
  "orderId"
 ],
 "type": "object"
}
```

### `query-party-city`

**描述：**

```
Description: 活动派对商品配置场次城市列表, 必须先确定spuId(从 mall-points-products 获取）或查询商品详情（从 mall-product-detail 获取)
When：
- 用户询问"主题派对在哪些城市"
- 用户询问"我想参加主题派对"
- 用户询问"生日类派对/主题类派对/麦麦体验营/品鉴会/读书会/积分兑换活动"
Preconditions：
- 必须先确定spuId（从 mall-points-products 获取或从 mall-product-detail获取）
Input:
- spuId: spuId 需要从查询可兑换商品列表（从 mall-points-products 获取）或查询商品详情（从 mall-product-detail 获取）中让用户选择一个spu，获取对应的skuId
```

**入参 Schema：**

```json
{
 "properties": {
  "spuId": {
   "description": "spuId",
   "type": "number"
  }
 },
 "required": [
  "spuId"
 ],
 "type": "object"
}
```

### `query-party-store`

**描述：**

```
Description: 查询指定城市下支持主题派对的门店列表。当用户选择了城市后，需要查看该城市有哪些门店可举办生日类派对/主题类派对/麦麦体验营/品鉴会/读书会/积分兑换活动时使用
Preconditions：
- 必须先通过 query-party-city 获取城市code和经纬度
- 必须先确定spuId（从 mall-points-products 获取或从 mall-product-detail获取）
Input:
- code: 城市code, 城市下的门店列表获取(query-party-city)
- latitude: 纬度, 城市下的门店列表获取(query-party-city)
- longitude: 经度, 城市下的门店列表获取(query-party-city)
- spuId: spuId, 从 mall-points-products 或 mall-product-detail 获取
```

**入参 Schema：**

```json
{
 "properties": {
  "code": {
   "description": "城市code",
   "type": "string"
  },
  "latitude": {
   "description": "纬度，从 query-party-city 返回结果的 data[].latitude 获取",
   "type": "number"
  },
  "longitude": {
   "description": "经度，从 query-party-city 返回结果的 data[].longitude 获取",
   "type": "number"
  },
  "spuId": {
   "description": "spuId，从 mall-points-products 或 mall-product-detail 获取",
   "type": "number"
  }
 },
 "required": [
  "code"
 ],
 "type": "object"
}
```

### `query-party-store-date`

**描述：**

```
Description: 查询指定门店支持生日类派对/主题类派对/麦麦体验营/品鉴会/读书会/积分兑换活动的可预约日期列表。当用户选择了门店后，需要查看该门店哪些日期可预约时使用。
When：
- 用户询问"这家店哪天可以预约"
- 用户询问"可预约日期"
- 用户询问"查看门店日历"
- 用户询问"哪天有场次"
- 用户选择门店后询问日期
Preconditions：
- 必须确定 spuId（从 mall-points-products 获取或从 mall-product-detail获取）
- 必须先通过 query-party-store 获取 storeCode
Input:
- storeCode: 门店code, 城市下的门店列表获取(query-party-store)
- spuId: spuId, 需要从查询可兑换商品列表（从 mall-points-products 获取）或查询商品详情（从 mall-product-detail 获取）中让用户选择一个spu，获取对应的skuId
```

**入参 Schema：**

```json
{
 "properties": {
  "spuId": {
   "description": "spuId",
   "type": "number"
  },
  "storeCode": {
   "description": "门店code",
   "type": "string"
  }
 },
 "required": [
  "spuId",
  "storeCode"
 ],
 "type": "object"
}
```

### `query-party-store-session`

**描述：**

```
Description: 查询指定门店、指定日期下的生日类派对/主题类派对/麦麦体验营/品鉴会/读书会/积分兑换活动场次列表。当用户选择了日期后，需要查看当天有哪些场次可预约时使用。
When：
- 用户询问"查看主题活动场次列表"
- 用户询问"几点有场次"
Preconditions：
- 必须确定 spuId（从 mall-points-products 获取或从 mall-product-detail获取）
- 必须先通过 query-party-store 获取 storeCode
- 必须先通过 query-party-store-date 获取 dateStr
Input:
- spuId: spuId, 需要从查询可兑换商品列表（从 mall-points-products 获取）或查询商品详情（从 mall-product-detail 获取）中让用户选择一个spu，获取对应的skuId
- storeCode: 门店code, 城市下的门店列表获取(query-party-store)
- dateStr: 门店日期, 城市下的门店列表获取(query-party-store-date)
```

**入参 Schema：**

```json
{
 "properties": {
  "dateStr": {
   "description": "门店日期",
   "type": "string"
  },
  "spuId": {
   "description": "spuId",
   "type": "number"
  },
  "storeCode": {
   "description": "门店code",
   "type": "string"
  }
 },
 "required": [
  "spuId",
  "storeCode",
  "dateStr"
 ],
 "type": "object"
}
```

### `query-promotions`

**描述：**

```
Description: 查询当前门店企业团餐场景下可用的促销规则（满减/满折），仅返回当前时间有效且适用在售餐品的规则原始数据
When：
- 企业团餐场景(beType=6)下，用户搭配方案前需要了解当前门店有哪些可用的促销活动/满减满折规则时
- 用户询问"有什么优惠"、"满多少减多少"、"打几折"时
Preconditions：
- 仅企业团餐场景(beType=6)可用
- 已通过 delivery-query-stores 获取 storeCode 和 beCode
Input:
- storeCode: 门店编码，必填
- beCode: 业务编码，团餐场景必传，与 storeCode 配对使用（从 delivery-query-stores 获取）
- orderType: 团餐场景固定传 2（外送）
- beType: 企业团餐固定传 6
- reservationDate: 预约场景必传，非预约场景不传。格式: yyyy-MM-dd HH:mm
Output:
- 返回当前门店有效的促销规则列表（原始结构），每条含 promotionId、promotionType、ruleCategory、beTypes、startTime、endTime、gmServiceCode、products、ruleDetail
- promotionType 含义：31-满额减，33-订单折扣
- ruleCategory 含义：30-满折/折扣，40-满减
- products 含义：适用餐品列表，type=1-包含、2-不包含、3-全部，productCode 为餐品编码
- 时间无效（已过期/未开始）或与在售餐品无交集的规则已被过滤
Next：
- 拿到规则后，由大模型自行根据规则解读优惠并计算搭配方案，工具不做最优推荐
```

**入参 Schema：**

```json
{
 "properties": {
  "beCode": {
   "description": "业务编码，与storeCode 配对使用，团餐场景必传（从 delivery-query-stores 获取）",
   "type": "string"
  },
  "beType": {
   "description": "业务类型，固定传 6（企业团餐）",
   "enum": [
    6
   ],
   "type": "integer"
  },
  "orderType": {
   "description": "订单类型，团餐场景固定传 2（外送）",
   "enum": [
    2
   ],
   "type": "integer"
  },
  "reservationDate": {
   "description": "预约场景必传，非预约场景不传。格式:yyyy-MM-dd HH:mm",
   "type": "string"
  },
  "storeCode": {
   "description": "门店编码（storeCode）, 不能为空",
   "type": "string"
  }
 },
 "required": [
  "storeCode",
  "orderType",
  "beType"
 ],
 "type": "object"
}
```

### `query-store-coupons`

**描述：**

```
Description: 查询【指定门店+订单类型】下可使用的优惠券，支持到店(orderType=1,含到店自取和得来速)和外送(orderType=2,含麦乐送和团餐)
When：
- 当用户已获取到门店时，用户询问"我有什么优惠券可以用"
- 当用户已获取到门店时，用户想在某门店下单前查看可用优惠
- 当用户已获取到门店时，用户选择了商品后想看能用哪些券
- 当用户已获取到门店时，用户问"这个门店能用什么券"
Input：
- storeCode: 门店编码，必填，
- orderType 和 beCode 传递规则（根据用户选择的 beType 确定）：
  到店自取(beType=1) → orderType=1，不传 beCode
  得来速(beType=5)   → orderType=1，必传 beCode（从 query-nearby-stores 获取）
  麦乐送(beType=2)   → orderType=2，必传 beCode（从 delivery-query-stores 获取）
  团餐(beType=6)     → orderType=2，必传 beCode（从 delivery-query-stores 获取）
- reservationDate: 预约场景必传，非预约场景不传。格式: yyyy-MM-dd HH:mm
```

**入参 Schema：**

```json
{
 "properties": {
  "beCode": {
   "description": "业务编码，与storeCode 配对使用，从query-nearby-stores或delivery-query-stores返回结果中获取。得来速(beType=5)/外送(orderType=2)/团餐场景必传，到店自取(beType=1)场景不传",
   "type": "string"
  },
  "beType": {
   "description": "1-到店取餐，2-麦乐送到家，5-得来速(DT)，6-企业团餐",
   "enum": [
    1,
    2,
    5,
    6
   ],
   "type": "integer"
  },
  "orderType": {
   "description": "订单类型, 1-到店（含到店自取+得来速车道取餐），2-外送（含麦乐送+企业团餐）",
   "enum": [
    1,
    2
   ],
   "type": "integer"
  },
  "reservationDate": {
   "description": "预约场景必传，非预约场景不传。格式 yyyy-MM-dd HH:mm",
   "type": "string"
  },
  "storeCode": {
   "description": "门店编码必须全部由数字组成",
   "type": "string"
  }
 },
 "required": [
  "orderType",
  "beType",
  "storeCode"
 ],
 "type": "object"
}
```

### `query-survey-coupon`

**描述：**

```
Description: 按订单号查询当前 MCP 用户本人订单的 CSAT 满意度答卷，并返回该订单关联奖券的标题、核销时间、核销状态和点餐方式。
When: 用户询问某个订单的满意度答卷结果时使用；用户询问某个订单关联奖券的内容、核销时间、是否已核销、适用于到店还是外送时使用。
Input: orderId 为用户提供的订单号；Agent 不要自行生成。
Next: 将返回的满意度描述、奖券标题、核销时间、核销状态和点餐方式告知用户；未返回的原始答卷、会员号、couponId、couponCode 不要猜测。
```

**入参 Schema：**

```json
{
 "properties": {
  "orderId": {
   "description": "订单号。必填。类型为字符串，仅允许字母、数字、下划线和连字符，最长 64 位，格式示例：1030108270000795607354880945。数据来源为用户明确提供的订单号或上游订单查询工具返回的订单号；Agent 不要自行编造或改写该值。",
   "type": "string"
  }
 },
 "required": [
  "orderId"
 ],
 "type": "object"
}
```