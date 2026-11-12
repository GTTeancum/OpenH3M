#pragma once
#include <atomic>
namespace rex::ui { class Presenter; }
namespace open_h3m::developer {
inline std::atomic<bool> uncapped{false};
inline std::atomic<rex::ui::Presenter*> presenter{nullptr};
inline std::atomic<int> capture_request{0};
inline std::atomic<int> capture_done{0};
}
