package runner

import (
	"github.com/projectdiscovery/gologger"
	updateutils "github.com/projectdiscovery/utils/update"
)

var banner = (`
   __                                           
  _____ _____  ______ ______   ___________ 
 /     \\__  \ \____ \\____ \_/ __ \_  __ \
|  Y Y  \/ __ \|  |_> >  |_> >  ___/|  | \/
|__|_|  (____  /   __/|   __/ \___  >__|   
      \/     \/|__|   |__|        \/       `)

var version = "v1.2.2"

// showBanner is used to show the banner to the user
func showBanner() {
	gologger.Print().Msgf("%s\n", banner)
	gologger.Print().Msgf("\t\tSEO DUO\n")
}

// GetUpdateCallback returns a callback function that updates katana
func GetUpdateCallback() func() {
	return func() {
		showBanner()
		updateutils.GetUpdateToolCallback("katana", version)()
	}
}
