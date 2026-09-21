"""
Unit test untuk metrik tambahan (revisi) di evaluate_matching.py.

Sengaja ditulis dengan `unittest` (bawaan Python, tanpa dependency baru)
supaya bisa dijalankan dengan DUA cara:

    python -m unittest test_metrics.py -v
    pytest test_metrics.py -v          # pytest bisa menjalankan unittest.TestCase juga

Setiap test memakai input kecil yang hasilnya bisa dihitung manual di kertas
(dijelaskan di komentar tiap test), supaya gampang diverifikasi bahwa
perhitungannya BENAR, bukan cuma "jalan tanpa error".

Catatan: import `evaluate_matching` di sini TIDAK butuh database atau NLP
service jalan -- modul itu hanya melakukan koneksi/network saat
run_evaluation() dipanggil eksplisit (lewat `if __name__ == "__main__"`),
bukan saat di-import.
"""
import math
import unittest

from evaluate_matching import (
    average_precision,
    coverage_indicator,
    diversity_at_k,
    infer_category,
    percentile,
    success_at_k,
)


class TestSuccessAtK(unittest.TestCase):
    def test_hit_within_k(self):
        # "b" relevan dan muncul di posisi ke-2 (dalam top-3) -> sukses.
        retrieved = ["a", "b", "c"]
        relevant = {"b"}
        self.assertEqual(success_at_k(retrieved, relevant, k=3), 1.0)

    def test_no_hit(self):
        # Tidak ada irisan sama sekali antara top-3 dan relevant -> gagal.
        retrieved = ["a", "b", "c"]
        relevant = {"z"}
        self.assertEqual(success_at_k(retrieved, relevant, k=3), 0.0)

    def test_hit_outside_k_but_inside_larger_k(self):
        # "e" relevan tapi ada di posisi ke-5 -> gagal untuk K=3, sukses K=5.
        retrieved = ["a", "b", "c", "d", "e"]
        relevant = {"e"}
        self.assertEqual(success_at_k(retrieved, relevant, k=3), 0.0)
        self.assertEqual(success_at_k(retrieved, relevant, k=5), 1.0)

    def test_empty_relevant_is_defined_as_zero(self):
        # relevant kosong -> secara definisi TIDAK PERNAH bisa "at least one
        # relevant result", jadi 0.0 (bukan None/undefined) -- lihat ASUMSI
        # di success_at_k().
        retrieved = ["a", "b", "c"]
        relevant = set()
        self.assertEqual(success_at_k(retrieved, relevant, k=3), 0.0)


class TestCoverageIndicator(unittest.TestCase):
    def test_empty_result_means_no_coverage(self):
        self.assertEqual(coverage_indicator([]), 0.0)

    def test_any_result_means_covered(self):
        self.assertEqual(coverage_indicator(["a"]), 1.0)
        self.assertEqual(coverage_indicator(["a", "b", "c"]), 1.0)


class TestAveragePrecision(unittest.TestCase):
    def test_classic_textbook_example(self):
        # Contoh standar buku teks IR:
        # retrieved = [d1, d2, d3, d4, d5], relevant = {d1, d3, d5} (3 relevan)
        # Posisi relevan: 1 (d1), 3 (d3), 5 (d5)
        #   P@1 = 1/1 = 1.0
        #   P@3 = 2/3 = 0.66667  (hits=2 di antara 3 diambil)
        #   P@5 = 3/5 = 0.6      (hits=3 di antara 5 diambil)
        # AP = (1.0 + 0.66667 + 0.6) / 3 (dibagi TOTAL relevan = 3)
        #    = 2.26667 / 3 = 0.755556
        retrieved = ["d1", "d2", "d3", "d4", "d5"]
        relevant = {"d1", "d3", "d5"}
        ap = average_precision(retrieved, relevant)
        self.assertAlmostEqual(ap, 0.755556, places=5)

    def test_no_relevant_found_in_retrieved(self):
        # Tidak ada dokumen relevan yang ketemu sama sekali di retrieved,
        # tapi relevant TIDAK kosong (dokumen relevannya ada, cuma tidak
        # ketemu) -> AP = 0.0 / len(relevant) = 0.0, BUKAN None.
        retrieved = ["x", "y"]
        relevant = {"z"}
        self.assertEqual(average_precision(retrieved, relevant), 0.0)

    def test_perfect_ranking(self):
        # Semua relevan ada di urutan paling atas -> AP = 1.0
        retrieved = ["r1", "r2", "other"]
        relevant = {"r1", "r2"}
        self.assertEqual(average_precision(retrieved, relevant), 1.0)

    def test_empty_relevant_returns_none(self):
        # Tidak terdefinisi secara matematis (pembagi = 0) -> None, supaya
        # dikecualikan dari rata-rata MAP (bukan dihitung sebagai 0).
        retrieved = ["a", "b"]
        relevant = set()
        self.assertIsNone(average_precision(retrieved, relevant))


class TestPercentile(unittest.TestCase):
    def test_median_of_five_values(self):
        # Median (P50) dari [1,2,3,4,5] jelas 3.
        self.assertEqual(percentile([1, 2, 3, 4, 5], 50), 3.0)

    def test_min_and_max(self):
        values = [5, 3, 1, 4, 2]  # sengaja tidak terurut
        self.assertEqual(percentile(values, 0), 1.0)
        self.assertEqual(percentile(values, 100), 5.0)

    def test_interpolation_between_two_points(self):
        # Dengan 2 nilai [10, 20] dan pct=95:
        #   rank = (2-1) * 0.95 = 0.95
        #   lower=0 (nilai 10), upper=1 (nilai 20), weight_upper=0.95
        #   hasil = 10*(1-0.95) + 20*0.95 = 0.5 + 19.0 = 19.5
        self.assertAlmostEqual(percentile([10, 20], 95), 19.5, places=5)

    def test_empty_list_returns_zero(self):
        self.assertEqual(percentile([], 95), 0.0)

    def test_single_value(self):
        self.assertEqual(percentile([42.0], 95), 42.0)


class TestDiversityAtK(unittest.TestCase):
    def test_all_same_category(self):
        retrieved = ["p1", "p2", "p3"]
        categories = {"p1": "batik", "p2": "batik", "p3": "batik"}
        self.assertEqual(diversity_at_k(retrieved, categories, k=3), 1.0)

    def test_all_different_categories(self):
        retrieved = ["p1", "p2", "p3"]
        categories = {"p1": "batik", "p2": "denim", "p3": "flanel"}
        self.assertEqual(diversity_at_k(retrieved, categories, k=3), 3.0)

    def test_fewer_results_than_k(self):
        # Cuma 2 hasil dikembalikan padahal k=3 -> diversity dihitung atas
        # 2 hasil itu saja (maksimum diversity otomatis terbatas jadi 2).
        retrieved = ["p1", "p2"]
        categories = {"p1": "batik", "p2": "denim"}
        self.assertEqual(diversity_at_k(retrieved, categories, k=3), 2.0)

    def test_empty_retrieved(self):
        self.assertEqual(diversity_at_k([], {}, k=3), 0.0)

    def test_unknown_product_id_falls_back_to_lainnya(self):
        # id yang tidak ada di kamus categories dianggap kategori 'lainnya'.
        retrieved = ["unknown1", "unknown2"]
        categories = {}
        self.assertEqual(diversity_at_k(retrieved, categories, k=3), 1.0)


class TestInferCategory(unittest.TestCase):
    def test_batik_keyword(self):
        product = {"title": "Kain Perca Batik Bersih", "description": "campur motif"}
        self.assertEqual(infer_category(product), "kain_perca_batik")

    def test_denim_keyword(self):
        product = {"title": "Limbah Denim Sisa Produksi", "description": "tebal dan kuat"}
        self.assertEqual(infer_category(product), "denim")

    def test_no_keyword_falls_back_to_lainnya(self):
        product = {"title": "Barang Tidak Dikenal", "description": "tidak ada kata kunci relevan"}
        self.assertEqual(infer_category(product), "lainnya")

    def test_word_boundary_avoids_false_positive(self):
        # "Perbandingan" mengandung substring "ban" (per-BAN-dingan) tapi
        # BUKAN sebagai kata utuh -- pola regex pakai \b (word boundary),
        # jadi tidak boleh salah ke-trigger jadi kategori 'karet_ban'.
        product = {"title": "Tabel Perbandingan Harga", "description": "tidak ada material di sini"}
        self.assertEqual(infer_category(product), "lainnya")


if __name__ == "__main__":
    unittest.main(verbosity=2)
