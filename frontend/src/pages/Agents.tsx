import { useEffect, useState } from 'react'
import { AppSidebar } from "@/components/app-sidebar"
// import { useUserContext } from '@/contexts/UserContext'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Separator } from "@/components/ui/separator"
import {
  SidebarInset,
  SidebarProvider,
} from "@/components/ui/sidebar"
import { ThemeProvider } from "@/components/theme-provider"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Plus, Download, Delete, Loader2} from "lucide-react"
import { Button } from "@/components/ui/button"


import { AgentsSetup } from '@/components/agents-setup';
import { ModeToggle } from '@/components/mode-toggle'
import { LoginCard } from "@/components/login";


import ag from '@/assets/ag.png';

import { getAvatarSrc } from '@/components/agents-definition'


// TODO: FUJ! How to get ENV vars from SWA?
// Define environment variables with default values
const BASE_URL = import.meta.env.VITE_BASE_URL || "local";
const ALLWAYS_LOGGED_IN =
  import.meta.env.VITE_ALLWAYS_LOGGED_IN === "true" ? true : false;
const ACTIVATION_CODE = import.meta.env.VITE_ACTIVATON_CODE || "0000";

// console.log('VITE_BASE_URL:', BASE_URL);
// console.log('VITE_ALLWAYS_LOGGED_IN:', ALLWAYS_LOGGED_IN);
// console.log('VITE_ACTIVATON_CODE:', ACTIVATION_CODE);


import { Footer } from '@/components/Footer'

import { Agent, Team, useTeamsContext } from '@/contexts/TeamsContext';

export default function Agents() {
  const { teams, loading, reloadTeams } = useTeamsContext();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<Team>(teams[0]);

  const [isAuthenticated, setIsAuthenticated] = useState(BASE_URL)
  // const { userInfo } = useUserContext();


  useEffect(() => {
    // console.log("Teams in consumer:", teams);
    if (teams.length > 0 && !selectedTeam) {
      setSelectedTeam(teams[0]);
      setAgents(teams[0].agents);
    }
  }, [teams]);
    
  /// TODO: better login -> MS EntraID
  const handleLogin = (email: string, password: string) => {
    console.log('Logging in with:', email)
    if (password === ACTIVATION_CODE || ALLWAYS_LOGGED_IN) {
      setIsAuthenticated(true)
    } else {
      console.log('Invalid activation code')
    }
  }

  // const handleLogout = () => {
  //   setIsAuthenticated(false)
  // }

  const handleTeamSelect = (team: Team) => {
    setAgents(team.agents);
    setSelectedTeam(team);
    console.log('Selected team:', selectedTeam.name);
    console.log('Selected agents:', agents);
  }

  if (loading) {
    return (
      <ThemeProvider defaultTheme="light" storageKey="vite-ui-theme">
        <SidebarProvider defaultOpen={true}>
          <AppSidebar onTeamSelect={handleTeamSelect} />
          <SidebarInset>
            <div className="flex items-center justify-center h-40">
              <Loader2 className="h-8 w-8 animate-spin" />  Initialzing...
            </div>
          </SidebarInset>
        </SidebarProvider>
      </ThemeProvider>
    );
  }

  return (
    <ThemeProvider defaultTheme="light" storageKey="vite-ui-theme">
    {!isAuthenticated ? (
      <LoginCard handleLogin={handleLogin} />
    ) : (
    <SidebarProvider defaultOpen={true}>
      <AppSidebar onTeamSelect={handleTeamSelect} />
      <SidebarInset>
        <header className="flex sticky top-0 bg-background h-14 shrink-0 items-center gap-2 border-b px-4 z-10 shadow">
          <div className="flex items-center gap-2 px-4 w-full">
            {/* <img src={banner} alt="Banner" className="h-64" /> */}
            {/* <SidebarTrigger />   */}
            {/* <Bot className="h-8 w-8" /> */}
            <img src={ag  } alt="Banner" className="h-8" />
            <Separator orientation="vertical" className="mr-2 h-4" />
            <Breadcrumb>
              <BreadcrumbList>
                <BreadcrumbItem className="hidden md:block">
                  <BreadcrumbLink href="#">
                    AutoGen & MagenticOne demo
                  </BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator className="hidden md:block" />
                <BreadcrumbItem>
                  <BreadcrumbPage>Library</BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
            <div className="ml-auto hidden items-center gap-2 md:flex">
        
   
            {/* <Separator orientation="vertical" className="mr-2 h-4" /> */}
            <ModeToggle />
            {/* <Separator orientation="vertical" className="mr-2 h-4" /> */}
            {/* {isAuthenticated ? (
              <Button variant="outline" onClick={handleLogout}>
                <LogOut />Log out
              </Button>
            ) : null} */}
                
            </div>
          </div>
        </header>
        {/* Main content */}
        <div className="flex flex-1 flex-col gap-4 p-4 pt-0">
          <Separator  />
          {/* Agents setup */}
          {teams.map((team) => (
            <div className="min-h-[100vh] flex-1 rounded-xl bg-muted/50 md:min-h-min">
              {/* Chat Interface */}
              <Card className={`md:col-span-2 flex flex-col`}>
                <CardHeader>
                  <CardTitle>{team.name}</CardTitle>
                  <Separator />
                  <div className="space-x-2 container">
                    <p className="text-sm text-muted-foreground inline">{team.description}</p>
                </div>
                </CardHeader>
                <CardContent className="flex-1 h-96">
                  
                  <AgentsSetup
                  team={team}
                  getAvatarSrc={getAvatarSrc}
                  isCollapsed={false}
                  />
                </CardContent>
                <CardFooter className="flex space-x-2">
           
                </CardFooter>
              </Card>
  
              
            </div> 
          ))}
          
          <div className="min-h-[100vh] flex-1 rounded-xl bg-muted/50 md:min-h-min">
            {/* Chat Interface */}
            <Card className={`md:col-span-2 flex flex-col`}>
              <CardHeader>
                <CardTitle>Team Management</CardTitle>
              </CardHeader>
              <CardContent className="flex-1 h-96">
                {/* <Separator className="my-2 invisible" /> */}
  
                <Button size="sm" variant="default" className="">
                  <Plus className="h-4 w-4" />
                  Create new team
                </Button>
                <Separator orientation="vertical" className="mr-2 h-4 invisible" />
                <Button variant="outline" size="sm">
                  <Download className="h-4 w-4" />
                  Download team specification
                </Button>
                <Separator orientation="vertical" className="mr-2 h-4 invisible" />
                <Button variant="destructive" size="sm">
                  <Delete className="h-4 w-4" />
                  Delete team
                </Button>
                <Separator orientation="vertical" className="mr-2 h-4 invisible" />
                <Button variant="default" size="sm" onClick={reloadTeams}>
                  Reload Teams
                </Button>
              </CardContent>
              <CardFooter className="flex space-x-2">
         
              </CardFooter>
            </Card>
          </div> 
        </div>
        {/* Footer */}
      <Footer />
      </SidebarInset>
    </SidebarProvider>
    )}
    </ThemeProvider>
  )
}
