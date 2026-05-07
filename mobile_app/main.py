from kivy.app import App
from kivy.uix.screenmanager import ScreenManager

from mobile_app.screens.home_screen import HomeScreen
from mobile_app.screens.dna_screen import DNAScreen
from mobile_app.screens.protein_screen import ProteinScreen
from mobile_app.screens.helix3d_screen import Helix3DScreen
from mobile_app.screens.guide_detail_screen import GuideDetailScreen



class HelixMobileApp(App):
    title = "Helix Mobile"

    def build(self):
        sm = ScreenManager()
        sm.add_widget(HomeScreen(name="home"))
        sm.add_widget(DNAScreen(name="dna"))
        sm.add_widget(ProteinScreen(name="protein"))
        sm.add_widget(Helix3DScreen(name="helix3d"))
        sm.add_widget(GuideDetailScreen(name="guide_detail"))

        return sm


if __name__ == "__main__":
    HelixMobileApp().run()
