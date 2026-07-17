"""Replace the generic mechanism with the locked technical explanation."""

from manim import (
    Arrow,
    Create,
    DOWN,
    Dot,
    FadeIn,
    FadeOut,
    MovingCameraScene,
    RoundedRectangle,
    Text,
    UP,
    VGroup,
    WHITE,
    YELLOW,
    config,
)


SCENE_TITLE = __SCENE_TITLE_JSON__
config.frame_width = 9
config.frame_height = 16
INK = "#F7F4EF"
MUTED = "#A5ADB8"
ACCENT = "#F5B642"
PANEL = "#20252D"


def labeled_panel(label: str) -> VGroup:
    panel = RoundedRectangle(
        corner_radius=0.18,
        width=5.8,
        height=1.7,
        stroke_color=MUTED,
        stroke_width=2,
        fill_color=PANEL,
        fill_opacity=1,
    )
    text = Text(label, font_size=40, color=INK)
    return VGroup(panel, text)


class __SCENE_CLASS__(MovingCameraScene):
    """A short vertical input-rule-output explainer scaffold."""

    def construct(self) -> None:
        title = Text(SCENE_TITLE, font_size=52, color=WHITE).to_edge(UP, buff=0.9)

        input_panel = labeled_panel("Input")
        rule_panel = labeled_panel("Rule").shift(3.0 * DOWN)
        output_panel = labeled_panel("Output").shift(6.0 * DOWN)
        VGroup(input_panel, rule_panel, output_panel).move_to(0.5 * DOWN)

        first_path = Arrow(
            input_panel.get_bottom(),
            rule_panel.get_top(),
            buff=0.15,
            color=MUTED,
            stroke_width=5,
        )
        second_path = Arrow(
            rule_panel.get_bottom(),
            output_panel.get_top(),
            buff=0.15,
            color=MUTED,
            stroke_width=5,
        )
        signal = Dot(input_panel.get_center(), radius=0.12, color=YELLOW)

        self.play(FadeIn(title, shift=0.2 * UP), run_time=0.5)
        self.play(FadeIn(input_panel), run_time=0.4)
        self.play(Create(first_path), FadeIn(rule_panel), run_time=0.7)
        self.play(signal.animate.move_to(rule_panel.get_center()), run_time=0.8)
        self.play(Create(second_path), FadeIn(output_panel), run_time=0.7)
        self.play(signal.animate.move_to(output_panel.get_center()), run_time=0.8)
        self.play(output_panel[0].animate.set_stroke(ACCENT, width=5), run_time=0.35)
        self.wait(0.45)
        self.play(FadeOut(signal), run_time=0.2)
