

db.kampanya_db.aggregate([
  {
    $group: {
      _id: "$banka",
      toplam: { $sum: 1 }
    }
  },
  {
    $sort: {
      toplam: -1
    }
  }
])