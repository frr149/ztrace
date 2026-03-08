import Foundation

// Función que consume ~70% del tiempo CPU
func heavyWork() {
    var sum: Double = 0
    for i in 0..<21_000_000 {
        sum += sin(Double(i))
    }
    // Evitar que el compilador optimice el cálculo
    if sum == .infinity { print("never") }
}

// Función que consume ~30% del tiempo CPU
func lightWork() {
    var sum: Double = 0
    for i in 0..<9_000_000 {
        sum += sin(Double(i))
    }
    if sum == .infinity { print("never") }
}

heavyWork()
lightWork()
