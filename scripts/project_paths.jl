# Project path configuration for MWorks/Syslab.
#
# Keep all fixed data paths here. The model scripts should import this file
# instead of duplicating source filenames.

const PROJECT_ROOT = normpath(joinpath(@__DIR__, ".."))
const SOURCE_ROOT = joinpath(PROJECT_ROOT, "original_source")
const OUTPUT_ROOT = joinpath(PROJECT_ROOT, "output")

const Q1_PROBLEM_PDF = joinpath(SOURCE_ROOT, "C题.pdf")
const ATTACHMENT_ROOT = joinpath(SOURCE_ROOT, "附件")

const ATTACHMENT_1 = joinpath(ATTACHMENT_ROOT, "附件1.xlsx")
const ATTACHMENT_2 = joinpath(ATTACHMENT_ROOT, "附件2.xlsx")
const ATTACHMENT_3 = joinpath(ATTACHMENT_ROOT, "附件3.xlsx")
const ATTACHMENT_4 = joinpath(ATTACHMENT_ROOT, "附件4.xlsx")

const TEMPLATE_ROOT = joinpath(ATTACHMENT_ROOT, "附件5")
const TEMPLATE_RESULT_1 = joinpath(TEMPLATE_ROOT, "result1.xlsx")
const TEMPLATE_RESULT_2 = joinpath(TEMPLATE_ROOT, "result2.xlsx")
const TEMPLATE_RESULT_3 = joinpath(TEMPLATE_ROOT, "result3.xlsx")
const TEMPLATE_RESULT_4_2 = joinpath(TEMPLATE_ROOT, "result4-2.xlsx")
const TEMPLATE_RESULT_4_3 = joinpath(TEMPLATE_ROOT, "result4-3.xlsx")

function q1_output_dir()
    return joinpath(OUTPUT_ROOT, "question_1")
end

function ensure_output_dirs()
    mkpath(OUTPUT_ROOT)
    mkpath(q1_output_dir())
    mkpath(joinpath(q1_output_dir(), "figures"))
end
