# Cleanliness Principles (Senior Engineer)

## Evidence (Primary Sources)
1. One codebase per app, many deploys; shared code sebaiknya jadi library terpisah.
- Source: https://12factor.net/codebase

2. Konsistensi style mempermudah pemahaman codebase besar.
- Source: https://google.github.io/styleguide/

3. Simple design rules (passes tests, no duplication, reveals intention, fewest elements) efektif sebagai filter kualitas desain.
- Source: https://martinfowler.com/bliki/BeckDesignRules.html

4. Refactoring = memperbaiki struktur internal tanpa mengubah perilaku eksternal, dilakukan dalam langkah kecil.
- Source: https://refactoring.com/

5. Commit convention yang eksplisit memudahkan histori, otomasi, dan komunikasi perubahan.
- Source: https://www.conventionalcommits.org/en/v1.0.0/

## Practical Translation
- Keep it small: batch perubahan kecil, verifikasi cepat.
- Keep it obvious: nama + alur harus menjelaskan niat.
- Keep it dry: hilangkan duplikasi yang jelas, jangan premature abstraction.
- Keep it stable: refactor bertahap, behavior tetap.
- Keep history clean: commit message terstruktur, satu intent utama.
