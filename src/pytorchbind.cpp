#include <torch/extension.h>  // to get the pybind11 stuff

#include "logsignature.hpp"  // signatory::logsignature_forward, signatory::logsignature_backward,
                             // signatory::make_lyndon_info
#include "misc.hpp"          // signatory::LogSignatureMode
#include "signature.hpp"     // signatory::signature_forward, signatory::signature_backward
#include "utilities.hpp"     // signatory::signature_channels, signatory::lyndon_words, signatory::lyndon_brackets,
                             // signatory::lyndon_words_to_basis_transform

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def("_logsignature_forward",
          &signatory::logsignature_forward,
          py::arg("path"), py::arg("depth"), py::arg("stream"), py::arg("basepoint"), py::arg("basepoint_value"),
          py::arg("mode"), py::arg("lyndon_info_capsule")=py::none);
    m.def("_logsignature_backward",
          &signatory::logsignature_backward);
    m.def("_make_lyndon_info",
        &signatory::make_lyndon_info);
    py::enum_<signatory::LogSignatureMode>(m, "_LogSignatureMode")
            .value("Expand", signatory::LogSignatureMode::Expand)
            .value("Brackets", signatory::LogSignatureMode::Brackets)
            .value("Words", signatory::LogSignatureMode::Words);
    m.def("_signature_forward",
          &signatory::signature_forward);
    m.def("_signature_backward",
          &signatory::signature_backward,
          py::arg("grad_out"), py::arg("backwards_info_capsule"), py::arg("clone")=true);
    m.def("_signature_channels",
          &signatory::signature_channels);
    m.def("_lyndon_words",
          &signatory::lyndon_words,
          py::return_value_policy::move);
    m.def("_lyndon_brackets",
          &signatory::lyndon_brackets,
          py::return_value_policy::move);
    m.def("_lyndon_words_to_basis_transform",
          &signatory::lyndon_words_to_basis_transform,
          py::return_value_policy::move);
}