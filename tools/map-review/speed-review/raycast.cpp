// Minimal BVH segment tester for static sightline analysis. Read-only on its inputs.
#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <thread>
#include <vector>

#define API extern "C" __declspec(dllexport)

struct V { float x, y, z; };
static inline V sub(V a, V b) { return {a.x - b.x, a.y - b.y, a.z - b.z}; }
static inline V cross(V a, V b) { return {a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x}; }
static inline float dot(V a, V b) { return a.x * b.x + a.y * b.y + a.z * b.z; }

struct Node { float lo[3], hi[3]; int left, right, first, count; };
static std::vector<V> T;          // 3 verts per triangle, reordered
static std::vector<Node> N;

static int build_rec(std::vector<int>& idx, std::vector<V>& c, const std::vector<V>& src, int b, int e) {
    Node n; for (int k = 0; k < 3; k++) { n.lo[k] = 1e30f; n.hi[k] = -1e30f; }
    float clo[3] = {1e30f, 1e30f, 1e30f}, chi[3] = {-1e30f, -1e30f, -1e30f};
    for (int i = b; i < e; i++) {
        for (int v = 0; v < 3; v++) {
            const float* p = &src[idx[i] * 3 + v].x;
            for (int k = 0; k < 3; k++) { n.lo[k] = std::min(n.lo[k], p[k]); n.hi[k] = std::max(n.hi[k], p[k]); }
        }
        const float* q = &c[idx[i]].x;
        for (int k = 0; k < 3; k++) { clo[k] = std::min(clo[k], q[k]); chi[k] = std::max(chi[k], q[k]); }
    }
    n.left = n.right = -1; n.first = b; n.count = e - b;
    int id = (int)N.size(); N.push_back(n);
    if (e - b <= 4) return id;
    int ax = 0; for (int k = 1; k < 3; k++) if (chi[k] - clo[k] > chi[ax] - clo[ax]) ax = k;
    if (chi[ax] - clo[ax] <= 0) return id;
    int mid = (b + e) / 2;
    std::nth_element(idx.begin() + b, idx.begin() + mid, idx.begin() + e, [&](int i, int j) { return (&c[i].x)[ax] < (&c[j].x)[ax]; });
    int l = build_rec(idx, c, src, b, mid); int r = build_rec(idx, c, src, mid, e);
    N[id].left = l; N[id].right = r; N[id].count = 0;
    return id;
}

API int rc_build(const float* tris, int n) {
    std::vector<V> src(n * 3); std::memcpy(src.data(), tris, sizeof(float) * 9 * (size_t)n);
    std::vector<V> c(n); std::vector<int> idx(n);
    for (int i = 0; i < n; i++) {
        idx[i] = i;
        c[i] = {(src[i * 3].x + src[i * 3 + 1].x + src[i * 3 + 2].x) / 3, (src[i * 3].y + src[i * 3 + 1].y + src[i * 3 + 2].y) / 3, (src[i * 3].z + src[i * 3 + 1].z + src[i * 3 + 2].z) / 3};
    }
    N.clear(); N.reserve(n); build_rec(idx, c, src, 0, n);
    T.resize(n * 3);
    for (int i = 0; i < n; i++) for (int v = 0; v < 3; v++) T[i * 3 + v] = src[idx[i] * 3 + v];
    return (int)N.size();
}

// Returns nearest hit parameter in (tmin,tmax) honouring the facing filter, or -1. sign receives dot(dir, normal) sign.
static float trace(V o, V d, float tmin, float tmax, int facing, bool any, int* sign) {
    float inv[3] = {1.0f / d.x, 1.0f / d.y, 1.0f / d.z};
    int stack[96]; int sp = 0; stack[sp++] = 0; float best = -1;
    while (sp) {
        const Node& n = N[stack[--sp]];
        float t0 = tmin, t1 = (best > 0 ? best : tmax);
        const float* op = &o.x;
        bool miss = false;
        for (int k = 0; k < 3; k++) {
            float a = (n.lo[k] - op[k]) * inv[k], b = (n.hi[k] - op[k]) * inv[k];
            if (a > b) std::swap(a, b);
            if (!(a == a) || !(b == b)) { if (op[k] < n.lo[k] || op[k] > n.hi[k]) { miss = true; break; } continue; }
            t0 = std::max(t0, a); t1 = std::min(t1, b);
            if (t0 > t1) { miss = true; break; }
        }
        if (miss) continue;
        if (n.left < 0) {
            for (int i = n.first; i < n.first + n.count; i++) {
                V v0 = T[i * 3], e1 = sub(T[i * 3 + 1], v0), e2 = sub(T[i * 3 + 2], v0);
                V nrm = cross(e1, e2); float dn = dot(d, nrm);
                if (facing > 0 && dn >= 0) continue;
                if (facing < 0 && dn <= 0) continue;
                V pv = cross(d, e2); float det = dot(e1, pv);
                if (std::fabs(det) < 1e-12f) continue;
                float id = 1.0f / det; V tv = sub(o, v0); float u = dot(tv, pv) * id;
                if (u < 0 || u > 1) continue;
                V qv = cross(tv, e1); float v = dot(d, qv) * id;
                if (v < 0 || u + v > 1) continue;
                float t = dot(e2, qv) * id;
                if (t <= tmin || t >= tmax) continue;
                if (best < 0 || t < best) { best = t; if (sign) *sign = dn < 0 ? -1 : 1; if (any) return best; }
            }
        } else if (sp < 94) { stack[sp++] = n.left; stack[sp++] = n.right; }
    }
    return best;
}

// For calibration: sign of dot(dir, normal) at the nearest hit of each ray (0 = no hit).
API void rc_first_facing(const float* origins, const float* dirs, int count, int* out) {
    for (int i = 0; i < count; i++) {
        V o = {origins[i * 3], origins[i * 3 + 1], origins[i * 3 + 2]}, d = {dirs[i * 3], dirs[i * 3 + 1], dirs[i * 3 + 2]};
        int s = 0; float t = trace(o, d, 1e-4f, 1e30f, 0, false, &s); out[i] = t > 0 ? s : 0;
    }
}

// Number of unobstructed segments between every point of A and every point of B (stops at `stop_after` if > 0).
API long long rc_clear_segments(const float* pa, int na, const float* pb, int nb, int facing, long long stop_after, int threads) {
    std::atomic<long long> clear(0); std::atomic<int> next(0);
    auto work = [&]() {
        for (;;) {
            int i = next.fetch_add(1); if (i >= na) return;
            if (stop_after > 0 && clear.load() >= stop_after) return;
            V a = {pa[i * 3], pa[i * 3 + 1], pa[i * 3 + 2]}; long long local = 0;
            for (int j = 0; j < nb; j++) {
                V b = {pb[j * 3], pb[j * 3 + 1], pb[j * 3 + 2]}; V d = sub(b, a);
                if (dot(d, d) < 1e-10f) { local++; continue; }
                if (trace(a, d, 1e-3f, 1.0f - 1e-3f, facing, true, nullptr) < 0) { local++; if (stop_after > 0) break; }
            }
            clear.fetch_add(local);
        }
    };
    std::vector<std::thread> pool; for (int t = 0; t < threads; t++) pool.emplace_back(work);
    for (auto& t : pool) t.join();
    return clear.load();
}

// For each point: how many of k fixed directions first hit a front face, a back face, or nothing.
// front = dot(dir, cross(e1,e2)) < 0.
API void rc_surroundings(const float* pts, int count, int k, int* front, int* back, int* miss, int threads) {
    std::vector<V> dirs(k);
    for (int i = 0; i < k; i++) {
        float z = 1.0f - 2.0f * (i + 0.5f) / k, r = std::sqrt(std::max(0.0f, 1.0f - z * z)), ph = i * 2.39996323f;
        dirs[i] = {r * std::cos(ph), r * std::sin(ph), z};
    }
    std::atomic<int> next(0);
    auto work = [&]() {
        for (;;) {
            int b = next.fetch_add(4096); if (b >= count) return;
            int e = std::min(count, b + 4096);
            for (int i = b; i < e; i++) {
                V o = {pts[i * 3], pts[i * 3 + 1], pts[i * 3 + 2]}; int f = 0, bk = 0, m = 0;
                for (int j = 0; j < k; j++) {
                    int s = 0; float t = trace(o, dirs[j], 1e-5f, 1e30f, 0, false, &s);
                    if (t < 0) m++; else if (s < 0) f++; else bk++;
                }
                front[i] = f; back[i] = bk; miss[i] = m;
            }
        }
    };
    std::vector<std::thread> pool; for (int t = 0; t < threads; t++) pool.emplace_back(work);
    for (auto& t : pool) t.join();
}

// For each point with a side normal: among k sphere directions on that side (dot > 0.15),
// count first hits on front faces, back faces, and misses.
API void rc_hemisphere(const float* pts, const float* nrm, int count, int k, int* front, int* back, int* miss, int threads) {
    std::vector<V> dirs(k);
    for (int i = 0; i < k; i++) {
        float z = 1.0f - 2.0f * (i + 0.5f) / k, r = std::sqrt(std::max(0.0f, 1.0f - z * z)), ph = i * 2.39996323f;
        dirs[i] = {r * std::cos(ph), r * std::sin(ph), z};
    }
    std::atomic<int> next(0);
    auto work = [&]() {
        for (;;) {
            int b = next.fetch_add(2048); if (b >= count) return;
            int e = std::min(count, b + 2048);
            for (int i = b; i < e; i++) {
                V o = {pts[i * 3], pts[i * 3 + 1], pts[i * 3 + 2]}, n = {nrm[i * 3], nrm[i * 3 + 1], nrm[i * 3 + 2]}; int f = 0, bk = 0, m = 0;
                for (int j = 0; j < k; j++) {
                    if (dot(dirs[j], n) <= 0.15f) continue;
                    int s = 0; float t = trace(o, dirs[j], 1e-5f, 1e30f, 0, false, &s);
                    if (t < 0) m++; else if (s < 0) f++; else bk++;
                }
                front[i] = f; back[i] = bk; miss[i] = m;
            }
        }
    };
    std::vector<std::thread> pool; for (int t = 0; t < threads; t++) pool.emplace_back(work);
    for (auto& t : pool) t.join();
}

// Simple preview render: nearest hit distance and |cos| between ray and surface normal (negative = back face).
API void rc_render(const float* origin, const float* dirs, int count, float* out_t, float* out_shade, int threads) {
    V o = {origin[0], origin[1], origin[2]}; std::atomic<int> next(0);
    auto work = [&]() {
        for (;;) {
            int b = next.fetch_add(4096); if (b >= count) return;
            int e = std::min(count, b + 4096);
            for (int i = b; i < e; i++) {
                V d = {dirs[i * 3], dirs[i * 3 + 1], dirs[i * 3 + 2]};
                float inv[3] = {1.0f / d.x, 1.0f / d.y, 1.0f / d.z};
                int stack[96]; int sp = 0; stack[sp++] = 0; float best = -1; float shade = 0;
                while (sp) {
                    const Node& n = N[stack[--sp]];
                    float t0 = 1e-4f, t1 = (best > 0 ? best : 1e30f); const float* op = &o.x; bool miss = false;
                    for (int k = 0; k < 3; k++) {
                        float a = (n.lo[k] - op[k]) * inv[k], bb = (n.hi[k] - op[k]) * inv[k];
                        if (a > bb) std::swap(a, bb);
                        if (!(a == a) || !(bb == bb)) { if (op[k] < n.lo[k] || op[k] > n.hi[k]) { miss = true; break; } continue; }
                        t0 = std::max(t0, a); t1 = std::min(t1, bb);
                        if (t0 > t1) { miss = true; break; }
                    }
                    if (miss) continue;
                    if (n.left < 0) {
                        for (int j = n.first; j < n.first + n.count; j++) {
                            V v0 = T[j * 3], e1 = sub(T[j * 3 + 1], v0), e2 = sub(T[j * 3 + 2], v0);
                            V nrm = cross(e1, e2); float dn = dot(d, nrm);
                            if (dn >= 0) continue;  // back faces are culled, as in game
                            V pv = cross(d, e2); float det = dot(e1, pv);
                            if (std::fabs(det) < 1e-12f) continue;
                            float id = 1.0f / det; V tv = sub(o, v0); float u = dot(tv, pv) * id;
                            if (u < 0 || u > 1) continue;
                            V qv = cross(tv, e1); float v = dot(d, qv) * id;
                            if (v < 0 || u + v > 1) continue;
                            float t = dot(e2, qv) * id;
                            if (t <= 1e-4f) continue;
                            if (best < 0 || t < best) { best = t; shade = -dn / (std::sqrt(dot(nrm, nrm)) * std::sqrt(dot(d, d)) + 1e-30f); }
                        }
                    } else if (sp < 94) { stack[sp++] = n.left; stack[sp++] = n.right; }
                }
                out_t[i] = best; out_shade[i] = shade;
            }
        }
    };
    std::vector<std::thread> pool; for (int t = 0; t < threads; t++) pool.emplace_back(work);
    for (auto& t : pool) t.join();
}
