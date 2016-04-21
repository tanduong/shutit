#The MIT License (MIT)
#
#Copyright (C) 2014 OpenBet Limited
#
#Permission is hereby granted, free of charge, to any person obtaining a copy of
#this software and associated documentation files (the "Software"), to deal in
#the Software without restriction, including without limitation the rights to
#use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
#of the Software, and to permit persons to whom the Software is furnished to do
#so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.
#
#THE SOFeWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#ITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
#THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#SOFTWARE.
"""Represents and manages a pexpect object for ShutIt's purposes.
"""

import pexpect
import shutit_util


class ShutItPexpectChild(object):

	def __init__(self,
				 shutit,
				 pexpect_child_id):
		"""
		"""
		self.check_exit			 = True
		self.expect				 = shutit.cfg['expect_prompts']['base_prompt']
		self.pexpect_child		  = None
		self.pexpect_child_id	   = pexpect_child_id
		self.login_stack			= []
		self.shutit_object		  = shutit


	def spawn_child(self,
					command,
					args=[],
					timeout=30,
					maxread=2000,
					searchwindowsize=None,
					logfile=None,
					cwd=None,
					env=None,
					ignore_sighup=False,
					echo=True,
					preexec_fn=None,
					encoding=None,
					codec_errors='strict',
					dimensions=None,
					delaybeforesend=0):
		"""spawn a child, and manage the delaybefore send setting to 0"""
		if self.pexpect_child != None:
			shutit_util.handle_exit(exit_code=1,msg='Cannot overwrite pexpect_child in object')
		self.pexpect_child = pexpect.spawn(command,
							 args=args,
							 timeout=timeout,
							 maxread=maxread,
							 searchwindowsize=searchwindowsize,
							 logfile=logfile,
							 cwd=cwd,
							 env=env,
							 ignore_sighup=ignore_sighup,
							 echo=echo,
							 preexec_fn=preexec_fn,
							 encoding=encoding,
							 codec_errors=codec_errors,
							 dimensions=dimensions)
		self.pexpect_child.delaybeforesend=delaybeforesend
		self.shutit_object.pexpect_children.append({self.pexpect_child_id:self.pexpect_child})
		return True




	def login(self,
			  user='root',
			  command='su -',
			  password=None,
			  prompt_prefix=None,
			  expect=None,
			  timeout=180,
			  escape=False,
			  note=None,
			  go_home=True,
			  delaybeforesend=0.05,
			  loglevel=logging.DEBUG):
		"""Logs the user in with the passed-in password and command.
		Tracks the login. If used, used logout to log out again.
		Assumes you are root when logging in, so no password required.
		If not, override the default command for multi-level logins.
		If passwords are required, see setup_prompt() and revert_prompt()

		@param user:			User to login with. Default: root
		@param command:		 Command to login with. Default: "su -"
		@param escape:		  See send(). We default to true here in case
								it matches an expect we add.
		@param password:		Password.
		@param prompt_prefix:   Prefix to use in prompt setup.
		@param expect:		  See send()
		@param timeout:		 How long to wait for a response. Default: 20.
		@param note:			See send()
		@param go_home:		 Whether to automatically cd to home.

		@type user:			 string
		@type command:		  string
		@type password:		 string
		@type prompt_prefix:	string
		@type timeout:		  integer
		"""
		# We don't get the default expect here, as it's either passed in, or a base default regexp.
		r_id = shutit_util.random_id()
		if prompt_prefix == None:
			prompt_prefix = r_id
		self.login_stack_append(r_id)
		cfg = self.shutit_object.cfg
		# Be helpful.
		if ' ' in user:
			self.shutit_object.fail('user has space in it - did you mean: login(command="' + user + '")?')
		if cfg['build']['delivery'] == 'bash' and command == 'su -':
			# We want to retain the current working directory
			command = 'su'
		if command == 'su -' or command == 'su' or command == 'login':
			send = command + ' ' + user
		else:
			send = command
		if expect == None:
			login_expect = cfg['expect_prompts']['base_prompt']
		else:
			login_expect = expect
		# We don't fail on empty before as many login programs mess with the output.
		# In this special case of login we expect either the prompt, or 'user@' as this has been seen to work.
		general_expect = [login_expect]
		# Add in a match if we see user+ and then the login matches. Be careful not to match against 'user+@...password:'
		general_expect = general_expect + [user+'@.*'+'[@#$]']
		# If not an ssh login, then we can match against user + @sign because it won't clash with 'user@adasdas password:'
		if not string.find(command,'ssh') == 0:
			general_expect = general_expect + [user+'@']
			general_expect = general_expect + ['.*[@#$]']
		if user == 'bash' and command == 'su -':
			self.shutit_object.log('WARNING! user is bash - if you see problems below, did you mean: login(command="' + user + '")?',level=loglevel.WARNING)
		self.shutit_object._handle_note(note,command=command + ', as user: "' + user + '"',training_input=send)
		# r'[^t] login:' - be sure not to match 'last login:'
		self.shutit_object,multisend(send,{'ontinue connecting':'yes','assword':password,r'[^t] login:':password},expect=general_expect,check_exit=False,timeout=timeout,fail_on_empty_before=False,escape=escape)
		if prompt_prefix != None:
			self.setup_prompt(r_id,shutit_pexpect_child=self,prefix=prompt_prefix)
		else:
			self.setup_prompt(r_id,shutit_pexpect_child=self)
		if go_home:
			self.shutit_object.send('cd',shutit_pexpect_child=self,check_exit=False, echo=False, loglevel=loglevel, delaybeforesend=delaybeforesend)
		self.shutit_object._handle_note_after(note=note)


	def logout(self,
			   expect=None,
			   command='exit',
			   note=None,
			   timeout=5,
			   delaybeforesend=0,
			   loglevel=logging.DEBUG):
		"""Logs the user out. Assumes that login has been called.
		If login has never been called, throw an error.

			@param shutit_pexpect_child:		   See send()
			@param expect:		  See send()
			@param command:		 Command to run to log out (default=exit)
			@param note:			See send()
		"""
		old_expect = expect or self.default_expect
		self._handle_note(note,training_input=command)
		if len(self.login_stack):
			current_prompt_name = self.login_stack.pop()
			if len(self.login_stack):
				old_prompt_name	 = self.login_stack[-1]
				# TODO: sort out global expect_prompts
				self.expect(self.shutit_object.cfg['expect_prompts'][old_prompt_name])
			else:
				# If none are on the stack, we assume we're going to the root prompt
				# set up in shutit_setup.py
				self.set_default_shutit_pexpect_child_expect()
		else:
			self.fail('Logout called without corresponding login', throw_exception=False)
		# No point in checking exit here, the exit code will be
		# from the previous command from the logged in session
		self.shutit_object.send(command, shutit_pexpect_child=self, expect=expect, check_exit=False, timeout=timeout,echo=False, loglevel=loglevel, delaybeforesend=delaybeforesend)
		self._handle_note_after(note=note)


	def login_stack_append(self,
						   r_id,
						   expect=None,
						   new_user=''):
		child = self.pexpect_child
		self.login_stack.append(r_id)


    def setup_prompt(self,
                     prompt_name,
                     prefix='default',
                     set_default_expect=True,
                     setup_environment=True,
                     delaybeforesend=0,
                     loglevel=logging.DEBUG):
        """Use this when you've opened a new shell to set the PS1 to something
        sane. By default, it sets up the default expect so you don't have to
        worry about it and can just call shutit.send('a command').

        If you want simple login and logout, please use login() and logout()
        within this module.

        Typically it would be used in this boilerplate pattern::

            shutit.send('su - auser', expect=shutit.cfg['expect_prompts']['base_prompt'], check_exit=False)
            shutit.setup_prompt('tmp_prompt')
            shutit.send('some command')
            [...]
            shutit.set_default_shutit_pexpect_child_expect()
            shutit.send('exit')

        This function is assumed to be called whenever there is a change
        of environment.

        @param prompt_name:         Reference name for prompt.
        @param prefix:              Prompt prefix. Default: 'default'
        @param shutit_pexpect_child:               See send()
        @param set_default_expect:  Whether to set the default expect
                                    to the new prompt. Default: True
        @param setup_environment:   Whether to setup the environment config

        @type prompt_name:          string
        @type prefix:               string
        @type set_default_expect:   boolean
        """
        local_prompt = prefix + '#' + shutit_util.random_id() + '> '
        cfg = self.cfg
        cfg['expect_prompts'][prompt_name] = local_prompt
        # Set up the PS1 value.
        # Unset the PROMPT_COMMAND as this can cause nasty surprises in the output.
        # Set the cols value, as unpleasant escapes are put in the output if the
        # input is > n chars wide.
        # The newline in the expect list is a hack. On my work laptop this line hangs
        # and times out very frequently. This workaround seems to work, but I
        # haven't figured out why yet - imiell.
        self.send((" export SHUTIT_BACKUP_PS1_%s=$PS1 && PS1='%s' && unset PROMPT_COMMAND && stty sane && stty cols " + str(cfg['build']['stty_cols'])) % (prompt_name, local_prompt), expect=['\r\n' + cfg['expect_prompts'][prompt_name]], fail_on_empty_before=False, timeout=5, shutit_pexpect_child=shutit_pexpect_child, echo=False, loglevel=loglevel, delaybeforesend=delaybeforesend)
        if set_default_expect:
            self.log('Resetting default expect to: ' + cfg['expect_prompts'][prompt_name],level=logging.DEBUG)
            self.set_default_shutit_pexpect_child_expect(cfg['expect_prompts'][prompt_name])
        # Ensure environment is set up OK.
        if setup_environment:
            self.setup_environment(prefix)

    def revert_prompt(self,                                                                                                                                                        
                      old_prompt_name,                                                                                                                                             
                      new_expect=None,                                                                                                                                             
                      delaybeforesend=0,                                                                                                                                           
                      shutit_pexpect_child=None):                                                                                                                                  
        """Reverts the prompt to the previous value (passed-in).                                                                                                                   
                                                                                                                                                                                   
        It should be fairly rare to need this. Most of the time you would just                                                                                                     
        exit a subshell rather than resetting the prompt.                                                                                                                          
                                                                                                                                                                                   
            - old_prompt_name -                                                                                                                                                    
            - new_expect      -                                                                                                                                                    
            - child           - See send()                                                                                                                                         
        """                                                                                                                                                                        
        expect = expect or self.default_expect                                                                                                  
        #     v the space is intentional, to avoid polluting bash history.                                                                                                         
        self.shutit_object.send((' PS1="${SHUTIT_BACKUP_PS1_%s}" && unset SHUTIT_BACKUP_PS1_%s') % (old_prompt_name, old_prompt_name), expect=expect, check_exit=False, fail_on_empty_before=False, echo=False, loglevel=logging.DEBUG,delaybeforesend=delaybeforesend)                                                                                      
        if not new_expect:                                                                                                                                                         
            self.log('Resetting default expect to default',level=logging.DEBUG)                                                                                                    
            self.set_default_shutit_pexpect_child_expect()                                                                                                                         
        self.setup_environment()       
>>>>>>> latest


	#DONE: replace get_default_child/set_default_child and expect with get_current_session or similar - shutit.current_shutit_pexpect_child
	#DONE: replace set default expect with 'set default pexpect child/expect'
	def send(self, string):
TODO: calls to util.send, and copy over code fom there
		self.pexpect_child.send(string)


	def sendline(self, string):
TODO: calls to util.send, and copy over code fom there
		self.pexpect_child.sendline(string)


	def expect(self,
			   expect,
			   timeout=None):
		"""Handle child expects, with EOF and TIMEOUT handled
		"""
		if type(expect) == str:
			expect = [expect]
		return self.pexpect_child.expect(expect + [pexpect.TIMEOUT] + [pexpect.EOF], timeout=timeout)


	#DONE: update references to check exit etc
	#DONE: replace get_default_child/set_default_child and expect with get_current_session or similar - shutit.current_shutit_pexpect_child
	#DONE: replace set default expect with 'set default pexpect child/expect'
	#DONE: move login stack into here and login_stack_append
	#TODO: update login, logout function
	#TODO: move shutit.login and logout and manage that in here
	#TODO: add a shutit.login function that passes through to default
	#TODO: move setup_environment
	#TODO: child.interact
	#TODO: child.before / child.after
	TODO: check shutit_pexpect_children references make sense (ie expect correct object)
	TODO: replace shutit.child_expect
	TODO: replace child.send and child.sendline
	TODO: replace refernces to 'host_child' and 'target_child'
	TODO: replace shutit_global.pexpect_children / self.pexpect_children
	TODO: replace get_pexpect_child
	TODO: child.logfile_send?
	TODO: child.expect
	TODO: setup_host_child
	TODO: setup_target_child
	TODO: child.close()
	TODO: child.exitstatus
	TODO: self.start_container
	TODO: _default_child, _default_expect

	FINALLY: any mention of child!




